"""문서 수집·임베딩 파이프라인
  1) financial_facts로부터 회사-연도별 '재무 요약 사실문서' 생성(항상 동작)
  2) data/docs/ 에 넣어둔 PDF/XLSX 파싱(있으면 멀티모달 확장)
각 세그먼트를 청킹→임베딩(KURE)→documents/document_chunks에 적재
"""
from __future__ import annotations

import glob
import os

from dotenv import load_dotenv

from embeddings import Embedder
from parsers.router import parse_file, SUPPORTED
from chunk import chunk_text
from ingest import db

DOCS_DIR = "data/docs"
SJ_NAMES = {
    "BS": "재무상태표", "IS": "손익계산서", "CIS": "포괄손익계산서",
    "CF": "현금흐름표", "SCE": "자본변동표",
}
KEY_ACCOUNTS = (
    "자산총계", "유동자산", "비유동자산", "부채총계", "유동부채", "비유동부채", "자본총계",
    "매출액", "영업수익", "수익(매출액)", "매출총이익", "영업이익", "당기순이익",
    "법인세비용차감전순이익", "영업활동현금흐름", "영업활동으로인한현금흐름",
)


def build_fact_documents(conn) -> list[tuple[dict, list[dict]]]:
    """정형 재무데이터 → 회사·연도별 요약 사실문서(세그먼트=재무제표 구분)."""
    placeholders = ", ".join(["%s"] * len(KEY_ACCOUNTS))
    sql = f"""
        SELECT c.corp_code, c.corp_name, c.industry, f.bsns_year, f.sj_div,
               f.account_nm, f.amount, f.source_url
        FROM financial_facts f
        JOIN companies c USING (corp_code)
        WHERE f.fs_div = 'CFS' AND f.sj_div IN ('BS','IS','CF')
          AND f.account_nm IN ({placeholders})
          AND f.amount IS NOT NULL
        ORDER BY c.corp_name, f.bsns_year, f.sj_div
    """
    with conn.cursor() as cur:
        cur.execute(sql, KEY_ACCOUNTS)
        rows = cur.fetchall()

    grouped: dict[tuple, dict] = {}
    for corp_code, corp_name, industry, year, sj_div, acct, amount, url in rows:
        g = grouped.setdefault((corp_code, corp_name, year), {"url": url, "industry": industry, "segs": {}})
        g["segs"].setdefault(sj_div, []).append(f"{acct}: {amount / 1_000_000:,.0f}백만원")

    bundles = []
    for (corp_code, corp_name, year), g in grouped.items():
        industry = g["industry"] or ""
        segments = []
        for sj_div, lines in g["segs"].items():
            sj_name = SJ_NAMES.get(sj_div, sj_div)
            text = (
                    f"{corp_name}({industry} 산업) {year}년 연결 {sj_name} (단위: 백만원)\n"
                    + "; ".join(lines)
                )
            segments.append({"locator": sj_name, "text": text})
        doc = {
            "doc_id": f"fact:{corp_code}:{year}",
            "source_type": "dart_fs",
            "corp_code": corp_code,
            "period": year,
            "title": f"{corp_name} {year} 연결재무제표 요약",
            "url": g["url"],
        }
        bundles.append((doc, segments))
    return bundles


def build_file_documents() -> list[tuple[dict, list[dict]]]:
    """data/docs/ 의 PDF/XLSX를 파싱하여 세그먼트로."""
    bundles = []
    if not os.path.isdir(DOCS_DIR):
        return bundles
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*"))):
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED:
            continue
        segments = parse_file(path)
        fname = os.path.basename(path)
        doc = {
            "doc_id": f"file:{fname}",
            "source_type": f"file{ext}",
            "corp_code": None,
            "period": None,
            "title": fname,
            "url": path,
        }
        bundles.append((doc, segments))
    return bundles


def ingest_bundle(conn, embedder, doc: dict, segments: list[dict]) -> int:
    db.upsert_document(conn, doc)
    db.delete_chunks(conn, doc["doc_id"])  # 재실행 시 중복 방지

    texts, metas = [], []
    for seg in segments:
        for piece in chunk_text(seg["text"]):
            texts.append(piece)
            metas.append({"locator": seg.get("locator")})
    if not texts:
        return 0

    vectors = embedder.encode(texts)
    records = [(doc["doc_id"], i, texts[i], vectors[i], metas[i]) for i in range(len(texts))]
    return db.insert_chunks(conn, records)


def main() -> None:
    load_dotenv()
    conn = db.get_conn()
    db.apply_schema(conn)
    db.register_pgvector(conn)

    print("임베딩 모델 로딩(KURE-v1)....")
    embedder = Embedder()
    print(f"임베딩 차원: {embedder.dim}")

    bundles = build_fact_documents(conn) + build_file_documents()
    total = 0
    for doc, segments in bundles:
        n = ingest_bundle(conn, embedder, doc, segments)
        total += n
        print(f"  - {doc['title']}: {n} chunks")
    print(f"완료. 문서 {len(bundles)}건, 총 {total} chunks 적재.")
    conn.close()


if __name__ == "__main__":
    main()
