from __future__ import annotations

import json

import tools

SYSTEM = """너는 한국 회계·재무 리서치 어시스턴트다. 다음 규칙을 반드시 지킨다.
1) 모든 재무 수치와 비율은 반드시 도구 호출 결과로만 답한다. 기억·어림짐작으로 숫자를 만들지 않는다.
2) 동종업계 비교는 compare_by_industry 도구를 사용한다.
3) 설명·배경 등 서술 근거가 필요하면 search_knowledge_base를 사용한다.
4) 도구가 데이터를 찾지 못하면(ok=false) 정직하게 모른다고 답하고 추정하지 않는다.
5) 최종 답변은 아래 JSON "만" 출력한다. 코드펜스나 다른 설명 없이 JSON만.
   {"answer": "<한국어 답변>", "confidence": "high|medium|low", "caveats": "<주의사항 또는 빈 문자열>"}
   sources와 tool_calls는 시스템이 채우므로 포함하지 않는다."""

MAX_STEPS = 6


def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {"answer": text.strip(), "confidence": "low", "caveats": "JSON 파싱 실패(원문 표시)"}


def _dedup_sources(sources: list) -> list:
    seen, out = set(), []
    for s in sources:
        key = (s.get("title"), s.get("locator"))
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


class Agent:
    def __init__(self, conn, embedder, llm):
        self.conn = conn
        self.embedder = embedder
        self.llm = llm

    def _dispatch(self, name: str, args: dict) -> dict:
        if name == "calculate_financial_ratio":
            return tools.calculate_financial_ratio(self.conn, **args)
        if name == "compare_by_industry":
            return tools.compare_by_industry(self.conn, **args)
        if name == "search_knowledge_base":
            return tools.search_knowledge_base(self.conn, self.embedder, **args)
        return {"ok": False, "error": f"알 수 없는 도구: {name}", "sources": []}

    def run(self, question: str) -> dict:
        messages = [{"role": "user", "content": question}]
        collected_sources, tool_log = [], []
        # 도구가 결정적으로 계산한 수치. 화면에서 LLM 문장과 분리해 계산식과 함께 표시한다.
        computed = []

        for _ in range(MAX_STEPS):
            resp = self.llm.create(system=SYSTEM, messages=messages, tools=tools.TOOL_DEFS)
            messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if b.type == "tool_use"]

            if not tool_uses:  # 도구 호출이 끝나면 최종 답변
                text = "".join(b.text for b in resp.content if b.type == "text")
                answer = _parse_json(text)
                answer["sources"] = _dedup_sources(collected_sources)
                answer["tool_calls"] = tool_log
                answer["computed"] = computed
                return answer

            results = []
            for tu in tool_uses:
                out = self._dispatch(tu.name, dict(tu.input))
                tool_log.append({"name": tu.name, "args": dict(tu.input), "ok": out.get("ok")})
                collected_sources.extend(out.get("sources", []))
                if tu.name == "calculate_financial_ratio" and out.get("ok"):
                    computed.append(out["result"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(out, ensure_ascii=False),
                })
            messages.append({"role": "user", "content": results})

        return {
            "answer": "단계 한도를 초과했습니다.",
            "confidence": "low",
            "caveats": "",
            "sources": _dedup_sources(collected_sources),
            "tool_calls": tool_log,
            "computed": computed,
        }
