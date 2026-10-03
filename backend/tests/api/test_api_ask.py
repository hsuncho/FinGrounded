from __future__ import annotations

from conftest import SAMPLE_RESULT, FakeAgent


def test_ask_returns_structured_answer(make_client):
    agent = FakeAgent(result=SAMPLE_RESULT)
    res = make_client(agent=agent).post("/api/ask", json={"question": "  삼성전자 2023년 부채비율은?  "})

    assert res.status_code == 200
    body = res.json()
    assert body["confidence"] == "high"
    assert body["sources"][0]["title"] == "삼성전자 2023 연결재무제표"
    assert body["computed"][0]["value"] == 25.36
    assert body["computed"][0]["inputs"]["부채총계"] == "92,228,115백만원"
    assert agent.questions == ["삼성전자 2023년 부채비율은?"]   # 앞뒤 공백 제거


def test_blank_question_is_rejected(make_client):
    client = make_client(agent=FakeAgent(result=SAMPLE_RESULT))
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "   "}).status_code == 422
    assert client.post("/api/ask", json={}).status_code == 422


def test_too_long_question_is_rejected(make_client):
    client = make_client(agent=FakeAgent(result=SAMPLE_RESULT))
    assert client.post("/api/ask", json={"question": "가" * 501}).status_code == 422


def test_agent_error_returns_502_without_leaking_details(make_client):
    agent = FakeAgent(error=RuntimeError("password=secret123 connection failed"))
    res = make_client(agent=agent).post("/api/ask", json={"question": "부채비율?"})

    assert res.status_code == 502
    assert "secret123" not in res.text


def test_malformed_llm_fields_are_normalized(make_client):
    raw = {"answer": "원문 텍스트", "confidence": "very sure", "sources": [], "tool_calls": []}
    res = make_client(agent=FakeAgent(result=raw)).post("/api/ask", json={"question": "질문"})

    assert res.status_code == 200
    body = res.json()
    assert body["confidence"] == "low"
    assert body["caveats"] == ""
    assert body["computed"] == []


def test_refusal_answer_passes_through(make_client):
    raw = {"answer": "삼성전자 2019년 재무데이터를 찾을 수 없습니다.", "confidence": "low", "caveats": "",
           "sources": [], "tool_calls": [{"name": "calculate_financial_ratio", "args": {}, "ok": False}],
           "computed": []}
    res = make_client(agent=FakeAgent(result=raw)).post("/api/ask", json={"question": "2019년 부채비율?"})

    assert res.status_code == 200
    assert res.json()["sources"] == []
    assert res.json()["tool_calls"][0]["ok"] is False
