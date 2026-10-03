from __future__ import annotations

import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from config import COMPANIES, BSNS_YEARS, REPRT_CODE, FS_DIV
from ingest.dart_client import OpenDartClient
from ingest import db


def parse_amount(raw) -> int | None:
    """'12,345' / '-' / '' 등을 정수로 정규화(결측은 None)."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if s in ("", "-"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return None


def source_url(corp_code: str, year: str, reprt: str, fs_div: str) -> str:
    return (
        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        f"?corp_code={corp_code}&bsns_year={year}&reprt_code={reprt}&fs_div={fs_div}"
    )


# financial_facts UNIQUE 제약(및 ON CONFLICT 타겟)과 동일한 키 인덱스
# (corp_code, bsns_year, reprt_code, fs_div, sj_div, account_id, account_nm, account_detail, ord)
# account_detail: SCE에서 자본항목(지배기업지분/비지배지분/합계 등)을 구분.
# ord: 표준계정코드가 없는 커스텀 계정에서 유동/비유동처럼 이름은 같지만 실제로는
#      다른 계정인 경우를 구분하는 유일한 값(account_detail도 비어있는 경우가 많음).
_CONFLICT_KEY_IDX = (0, 1, 2, 3, 4, 6, 7, 8, 12)
_CONFLICT_KEY_NAMES = (
    "corp_code", "bsns_year", "reprt_code", "fs_div", "sj_div",
    "account_id", "account_nm", "account_detail", "ord",
)
_FIELD_NAMES = (
    "corp_code", "bsns_year", "reprt_code", "fs_div", "sj_div", "sj_nm",
    "account_id", "account_nm", "account_detail", "amount", "prev_amount",
    "currency", "ord", "source_url",
)


def dedupe_records(
    records: list[tuple], label: str = "", mismatch_log_path: str | None = None
) -> tuple[list[tuple], int, int]:
    """ON CONFLICT 키 기준으로 중복 레코드를 제거한다(마지막 값 채택).

    DART 응답에는 account_id가 비어 있거나 account_nm이 반복되는 계정이 섞여 있어
    같은 배치 안에 동일 키가 여러 번 등장할 수 있다. execute_values의
    ON CONFLICT DO UPDATE는 한 명령 내 같은 행을 두 번 갱신하지 못해
    CardinalityViolation이 나므로, 적재 직전에 걸러낸다.

    값이 서로 다른 중복 그룹은 콘솔에 개별 출력하는 대신 mismatch_log_path(JSONL)에
    한 줄씩 기록한다(콘솔 스팸 방지 + 후속 검증용). 반환값은
    (정제된 레코드, 제거 건수, 값 불일치 그룹 수).
    """
    grouped: dict[tuple, list[tuple]] = {}
    order: list[tuple] = []
    for rec in records:
        key = tuple(rec[i] for i in _CONFLICT_KEY_IDX)
        if key not in grouped:
            order.append(key)
            grouped[key] = []
        grouped[key].append(rec)

    removed = 0
    diff_groups = 0
    deduped = []
    mismatch_entries = []
    for key in order:
        group = grouped[key]
        if len(group) > 1:
            removed += len(group) - 1
            rest_values = {tuple(v for i, v in enumerate(rec) if i not in _CONFLICT_KEY_IDX) for rec in group}
            if len(rest_values) > 1:
                diff_groups += 1
                mismatch_entries.append(
                    {
                        "run_label": label,
                        "key": dict(zip(_CONFLICT_KEY_NAMES, key)),
                        "group_size": len(group),
                        "chosen": dict(zip(_FIELD_NAMES, group[-1])),
                        "candidates": [dict(zip(_FIELD_NAMES, rec)) for rec in group],
                    }
                )
        deduped.append(group[-1])

    if mismatch_entries and mismatch_log_path:
        with open(mismatch_log_path, "a", encoding="utf-8") as f:
            for entry in mismatch_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if removed:
        dup_group_count = sum(1 for k in order if len(grouped[k]) > 1)
        detail = f", 상세 -> {mismatch_log_path}" if mismatch_entries and mismatch_log_path else ""
        print(
            f"    [중복] {label} 중복 {removed}건 제거(그룹 {dup_group_count}개, "
            f"값 불일치 {diff_groups}개){detail}"
        )
    return deduped, removed, diff_groups


def main() -> None:
    load_dotenv()
    client = OpenDartClient(os.environ.get("OPENDART_API_KEY", ""))
    conn = db.get_conn()
    db.apply_schema(conn)

    os.makedirs("logs", exist_ok=True)
    mismatch_log_path = os.path.join(
        "logs", f"dedupe_mismatches_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    )

    print("corpCode 매핑 다운로드 중...")
    code_map = client.fetch_corp_code_map()

    total = 0
    total_removed = 0
    total_mismatch_groups = 0
    for c in COMPANIES:
        corp_code = code_map.get(c.stock_code)
        if not corp_code:
            print(f"[경고] {c.name}({c.stock_code}) 고유번호 미발견 — 건너뜀")
            continue
        db.upsert_company(conn, corp_code, c.name, c.stock_code, c.industry)

        for year in BSNS_YEARS:
            rows = client.fetch_full_financials(corp_code, year, REPRT_CODE, FS_DIV)
            if not rows:
                print(f"  - {c.name} {year}: 데이터 없음")
                continue
            src = source_url(corp_code, year, REPRT_CODE, FS_DIV)
            records = [
                (
                    corp_code, year, REPRT_CODE, FS_DIV,
                    r.get("sj_div") or "", r.get("sj_nm"),
                    r.get("account_id") or "", r.get("account_nm") or "",
                    r.get("account_detail") or "",
                    parse_amount(r.get("thstrm_amount")),
                    parse_amount(r.get("frmtrm_amount")),
                    r.get("currency"),
                    int(r["ord"]) if str(r.get("ord", "")).strip().isdigit() else None,
                    src,
                )
                for r in rows
            ]
            records, removed, diff_groups = dedupe_records(
                records, label=f"{c.name} {year}", mismatch_log_path=mismatch_log_path
            )
            total_removed += removed
            total_mismatch_groups += diff_groups
            n = db.upsert_financial_facts(conn, records)
            total += n
            print(f"  - {c.name} {year}: {n}건 적재")
            time.sleep(0.3)  # rate limit 배려

    print(f"완료. 총 {total}건 재무 데이터 적재.")
    if total_removed:
        print(
            f"중복 제거 총 {total_removed}건(값 불일치 그룹 {total_mismatch_groups}개). "
            f"상세 로그: {mismatch_log_path}"
        )
    conn.close()


if __name__ == "__main__":
    main()
