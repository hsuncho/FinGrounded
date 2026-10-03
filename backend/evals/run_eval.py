"""평가 러너. 골든셋을 Agent로 실행하고 유형별 지표를 채점.

지표
 - tool_selection : 기대한 도구를 호출했는가
 - numeric        : 답변의 수치가 도구가 계산한 정답과 tol 이내로 일치(근거성=수치)
 - refusal        : 데이터 없는 질문을 정직하게 거부했는가
 - comparison     : 비교 도구 호출 + 대상 기업이 모두 답변에 등장
 - grounding      : 비거부 답변에 출처가 존재하는가
 - retrieval Hit@k: 검색 상위 k에 정답 문서가 포함되는가

정답(ground truth)은 하드코딩하지 않고 tools로 계산"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

import tools
import retriever
from embeddings import Embedder
from ingest import db
from llm import LLM
from agent import Agent
from evals import evaluators as ev

GOLDEN = Path(__file__).with_name("golden_set.jsonl")
REPORT = Path(__file__).with_name("report.json")
NUMERIC_TOL = 0.5  # 절대 %p 허용오차


def load_golden() -> list[dict]:
    items = []
    with open(GOLDEN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def score_item(item: dict, agent: Agent, conn, embedder) -> dict:
    t = item["type"]
    exp = item["expect"]
    checks: dict[str, bool] = {}

    if t == "retrieval":
        results = retriever.search(conn, embedder, item["question"], k=exp.get("k", 3))
        titles = [r["title"] for r in results]
        checks["retrieval_hit"] = any(exp["title_contains"] in ti for ti in titles)
        return {"id": item["id"], "type": t, "checks": checks,
                "detail": {"top_titles": titles}}

    # Agent 실행 (수치·비교·거부)
    ans = agent.run(item["question"])
    answer, sources = ans.get("answer", ""), ans.get("sources", [])
    called = [c["name"] for c in ans.get("tool_calls", [])]

    if t == "numeric":
        checks["tool_selection"] = exp["tool"] in called
        gt = tools.calculate_financial_ratio(conn, exp["company"], exp["year"], exp["ratio"])
        if gt.get("ok"):
            truth = gt["result"]["value"]
            checks["numeric"] = ev.numeric_match(answer, truth, NUMERIC_TOL)
        else:
            checks["numeric"] = False  # 정답 계산 불가 → 골든셋 점검 필요
        checks["grounding"] = ev.has_grounding(answer, sources)

    elif t == "comparison":
        checks["tool_selection"] = exp["tool"] in called
        gt = tools.compare_by_industry(conn, exp["industry"], exp["metric"], exp["year"])
        names = [r["company"] for r in gt["result"]["ranking"]] if gt.get("ok") else []
        checks["comparison"] = bool(names) and ev.contains_all(answer, names)
        checks["grounding"] = ev.has_grounding(answer, sources)

    elif t == "refusal":
        checks["refusal"] = ev.is_refusal(answer, sources)

    return {"id": item["id"], "type": t, "checks": checks,
            "detail": {"answer": answer[:120], "tools": called}}


def aggregate(results: list[dict]) -> dict:
    buckets: dict[str, list[bool]] = {}
    for r in results:
        for name, ok in r["checks"].items():
            buckets.setdefault(name, []).append(bool(ok))
    metrics = {k: round(sum(v) / len(v), 3) for k, v in buckets.items()}
    per_item_pass = [all(r["checks"].values()) for r in results if r["checks"]]
    metrics["overall_pass_rate"] = round(sum(per_item_pass) / len(per_item_pass), 3)
    return metrics


def main() -> dict:
    load_dotenv()
    conn = db.get_conn()
    db.register_pgvector(conn)
    embedder = Embedder()
    agent = Agent(conn, embedder, LLM())

    items = load_golden()
    results = []
    for it in items:
        r = score_item(it, agent, conn, embedder)
        results.append(r)
        flags = " ".join(f"{k}={'O' if v else 'X'}" for k, v in r["checks"].items())
        print(f"[{r['type']:10}] {r['id']:24} {flags}")

    metrics = aggregate(results)
    report = {"tolerance_pp": NUMERIC_TOL, "n_items": len(items),
              "metrics": metrics, "results": results}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 지표 요약 =====")
    for k, v in metrics.items():
        print(f"  {k:20} {v}")
    print(f"\n리포트 저장: {REPORT}")
    conn.close()
    return report


if __name__ == "__main__":
    main()
