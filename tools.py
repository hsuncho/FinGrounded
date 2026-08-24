from __future__ import annotations

import retriever

# 계정명 별칭 (DART 표기 흔들림 흡수)
ACCOUNT_ALIASES = {
    "부채총계": ["부채총계"],
    "자본총계": ["자본총계"],
    "자산총계": ["자산총계"],
    "유동자산": ["유동자산"],
    "유동부채": ["유동부채"],
    "당기순이익": ["당기순이익", "당기순이익(손실)"],
    "영업이익": ["영업이익", "영업이익(손실)"],
    "매출액": ["매출액", "영업수익", "수익(매출액)", "매출"],
}

# 비율 정의: 슬롯, 계산식, 단위
RATIOS = {
    "부채비율":   (["부채총계", "자본총계"], lambda v: v["부채총계"] / v["자본총계"] * 100, "%"),
    "유동비율":   (["유동자산", "유동부채"], lambda v: v["유동자산"] / v["유동부채"] * 100, "%"),
    "ROE":       (["당기순이익", "자본총계"], lambda v: v["당기순이익"] / v["자본총계"] * 100, "%"),
    "영업이익률": (["영업이익", "매출액"],   lambda v: v["영업이익"] / v["매출액"] * 100, "%"),
    "순이익률":   (["당기순이익", "매출액"],  lambda v: v["당기순이익"] / v["매출액"] * 100, "%"),
}


def compute_ratio(ratio: str, values: dict) -> float:
    """순수 계산 함수(DB 없이 오프라인 테스트 가능)."""
    _, fn, _ = RATIOS[ratio]
    return fn(values)


def resolve_company(conn, name: str):
    with conn.cursor() as cur:
        cur.execute("SELECT corp_code, corp_name, industry FROM companies WHERE corp_name=%s", (name,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT corp_code, corp_name, industry FROM companies WHERE corp_name ILIKE %s",
                (f"%{name}%",),
            )
            row = cur.fetchone()
    return row  # (corp_code, corp_name, industry) or None


def fetch_accounts(conn, corp_code: str, year: str):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT account_nm, amount, source_url FROM financial_facts
               WHERE corp_code=%s AND bsns_year=%s AND fs_div='CFS' AND amount IS NOT NULL""",
            (corp_code, year),
        )
        rows = cur.fetchall()
    by_name, url = {}, None
    for acct, amount, src in rows:
        by_name.setdefault(acct, float(amount))
        url = url or src
    return by_name, url


def _resolve_slots(by_name: dict, slots: list) -> dict:
    values = {}
    for slot in slots:
        for cand in ACCOUNT_ALIASES.get(slot, [slot]):
            if cand in by_name:
                values[slot] = by_name[cand]
                break
        if slot not in values:
            raise KeyError(slot)
    return values


def _account_source(corp_name, year, url, locator):
    return {"title": f"{corp_name} {year} 연결재무제표", "url": url, "locator": locator}


def calculate_financial_ratio(conn, company: str, year: str, ratio: str) -> dict:
    if ratio not in RATIOS:
        return {"ok": False, "error": f"지원하지 않는 비율: {ratio}", "sources": []}
    comp = resolve_company(conn, company)
    if not comp:
        return {"ok": False, "error": f"회사를 찾을 수 없음: {company}", "sources": []}
    corp_code, corp_name, _ = comp
    by_name, url = fetch_accounts(conn, corp_code, year)
    if not by_name:
        return {"ok": False, "error": f"{corp_name} {year} 재무데이터 없음", "sources": []}
    slots, _, unit = RATIOS[ratio]
    try:
        values = _resolve_slots(by_name, slots)
        val = compute_ratio(ratio, values)
    except KeyError as e:
        return {"ok": False, "error": f"필요 계정 누락: {e.args[0]}", "sources": []}
    except ZeroDivisionError:
        return {"ok": False, "error": "분모가 0", "sources": []}
    inputs = {k: f"{v / 1_000_000:,.0f}백만원" for k, v in values.items()}
    return {
        "ok": True,
        "result": {
            "company": corp_name, "year": year, "ratio": ratio,
            "value": round(val, 2), "unit": unit, "inputs": inputs,
        },
        "sources": [_account_source(corp_name, year, url, "재무제표")],
    }


def compare_by_industry(conn, industry: str, metric: str, year: str) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT corp_code, corp_name FROM companies WHERE industry=%s", (industry,))
        comps = cur.fetchall()
    if not comps:
        return {"ok": False, "error": f"해당 산업 기업 없음: {industry}", "sources": []}

    items, sources = [], []
    for corp_code, corp_name in comps:
        by_name, url = fetch_accounts(conn, corp_code, year)
        if not by_name:
            continue
        if metric in RATIOS:
            slots, _, unit = RATIOS[metric]
            try:
                val = round(compute_ratio(metric, _resolve_slots(by_name, slots)), 2)
            except (KeyError, ZeroDivisionError):
                continue
        else:
            found = None
            for cand in ACCOUNT_ALIASES.get(metric, [metric]):
                if cand in by_name:
                    found = by_name[cand]
                    break
            if found is None:
                continue
            val, unit = round(found / 1_000_000), "백만원"
        items.append({"company": corp_name, "value": val, "unit": unit})
        sources.append(_account_source(corp_name, year, url, metric))

    if not items:
        return {"ok": False, "error": f"{industry} {year} {metric} 계산 불가", "sources": []}
    items.sort(key=lambda x: x["value"], reverse=True)
    return {
        "ok": True,
        "result": {"industry": industry, "metric": metric, "year": year, "ranking": items},
        "sources": sources,
    }


def search_knowledge_base(conn, embedder, query: str, k: int = 4) -> dict:
    results = retriever.search(conn, embedder, query, k=k)
    if not results:
        return {"ok": False, "error": "검색 결과 없음", "sources": []}
    return {
        "ok": True,
        "result": [
            {
                "content": r["content"],
                "score": round(r["score"], 3),
                "cite": r["title"] + (f" · {r['locator']}" if r["locator"] else ""),
            }
            for r in results
        ],
        "sources": [
            {"title": r["title"], "url": r["url"], "locator": r["locator"]} for r in results
        ],
    }


# ---- Anthropic 도구 스키마 ----
TOOL_DEFS = [
    {
        "name": "calculate_financial_ratio",
        "description": "특정 기업·연도의 재무비율을 DB 정형데이터로 정확히 계산한다. 비율 수치가 필요하면 반드시 이 도구를 사용한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "기업명 (예: 삼성전자)"},
                "year": {"type": "string", "description": "사업연도 4자리 (예: 2023)"},
                "ratio": {"type": "string", "enum": list(RATIOS.keys())},
            },
            "required": ["company", "year", "ratio"],
        },
    },
    {
        "name": "compare_by_industry",
        "description": "같은 산업군 내 모든 기업에 대해 지정 지표(비율명 또는 계정명)를 계산·정렬한다. 동종업계 비교에 사용한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "산업군 (예: 반도체, 인터넷, 자동차)"},
                "metric": {"type": "string", "description": "비율명(부채비율/유동비율/ROE/영업이익률/순이익률) 또는 계정명(매출액/자산총계 등)"},
                "year": {"type": "string", "description": "사업연도 4자리"},
            },
            "required": ["industry", "metric", "year"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "재무·공시 지식베이스에서 서술형 근거를 검색한다. 수치 계산이 아닌 설명·맥락이 필요할 때 사용한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색 질의(한국어)"},
                "k": {"type": "integer", "description": "결과 개수(기본 4)"},
            },
            "required": ["query"],
        },
    },
]
