"""Agent가 계산 도구 결과를 computed로 내보내는지 검증(LLM·DB 없이 실행)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import agent as agent_mod
from agent import Agent


def tool_use(id_, name, **args):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=args)


def text(s):
    return SimpleNamespace(type="text", text=s)


class ScriptedLLM:
    """미리 정한 응답을 순서대로 돌려주는 가짜 LLM."""

    def __init__(self, *turns):
        self.turns = list(turns)

    def create(self, system, messages, tools):
        return SimpleNamespace(content=self.turns.pop(0))


FINAL = text(json.dumps({"answer": "답변", "confidence": "high", "caveats": ""}, ensure_ascii=False))


def fake_calc(conn, company, year, ratio):
    if year == "2019":
        return {"ok": False, "error": "데이터 없음", "sources": []}
    return {
        "ok": True,
        "result": {"company": company, "year": year, "ratio": ratio, "value": 25.36, "unit": "%",
                   "inputs": {"부채총계": "1백만원", "자본총계": "4백만원"}},
        "sources": [{"title": f"{company} {year} 연결재무제표", "url": "u", "locator": "재무제표"}],
    }


def test_successful_calculation_is_exposed_as_computed(monkeypatch):
    monkeypatch.setattr(agent_mod.tools, "calculate_financial_ratio", fake_calc)
    llm = ScriptedLLM(
        [tool_use("t1", "calculate_financial_ratio", company="삼성전자", year="2023", ratio="부채비율")],
        [FINAL],
    )
    out = Agent(conn=None, embedder=None, llm=llm).run("삼성전자 2023 부채비율")

    assert out["computed"] == [fake_calc(None, "삼성전자", "2023", "부채비율")["result"]]
    assert out["tool_calls"][0]["ok"] is True


def test_failed_calculation_is_not_in_computed(monkeypatch):
    monkeypatch.setattr(agent_mod.tools, "calculate_financial_ratio", fake_calc)
    llm = ScriptedLLM(
        [tool_use("t1", "calculate_financial_ratio", company="삼성전자", year="2019", ratio="부채비율")],
        [FINAL],
    )
    out = Agent(conn=None, embedder=None, llm=llm).run("삼성전자 2019 부채비율")

    assert out["computed"] == []
    assert out["tool_calls"][0]["ok"] is False


def test_no_tool_call_means_empty_computed():
    out = Agent(conn=None, embedder=None, llm=ScriptedLLM([FINAL])).run("안녕")
    assert out["computed"] == []


def test_step_limit_response_keeps_computed(monkeypatch):
    monkeypatch.setattr(agent_mod.tools, "calculate_financial_ratio", fake_calc)
    turns = [[tool_use(f"t{i}", "calculate_financial_ratio", company="삼성전자", year="2023", ratio="부채비율")]
             for i in range(agent_mod.MAX_STEPS)]
    out = Agent(conn=None, embedder=None, llm=ScriptedLLM(*turns)).run("반복")

    assert out["answer"] == "단계 한도를 초과했습니다."
    assert len(out["computed"]) == agent_mod.MAX_STEPS
