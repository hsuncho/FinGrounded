"""API 테스트 공용 픽스처. DB·임베딩 모델·Anthropic API 없이 동작."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api.deps import get_agent
from api.main import create_app


class FakePool:
    def __init__(self, db_ok: bool = True):
        self.db_ok = db_ok

    def closeall(self):
        pass


class FakeServices:
    def __init__(self, db_ok: bool = True):
        self.pool = FakePool(db_ok)
        self.embedder = None
        self.llm = None

    def check_db(self):
        if not self.pool.db_ok:
            raise RuntimeError("db down")

    def close(self):
        pass


class FakeAgent:
    """Agent.run()과 같은 모양의 dict를 돌려주는 가짜."""

    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.questions: list[str] = []

    def run(self, question: str) -> dict:
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.result


SAMPLE_RESULT = {
    "answer": "삼성전자의 2023년 부채비율은 25.36%입니다.",
    "confidence": "high",
    "caveats": "",
    "sources": [{"title": "삼성전자 2023 연결재무제표", "url": "https://opendart.fss.or.kr/x", "locator": "재무제표"}],
    "tool_calls": [{"name": "calculate_financial_ratio",
                    "args": {"company": "삼성전자", "year": "2023", "ratio": "부채비율"}, "ok": True}],
    "computed": [{"company": "삼성전자", "year": "2023", "ratio": "부채비율", "value": 25.36, "unit": "%",
                  "inputs": {"부채총계": "92,228,115백만원", "자본총계": "363,677,865백만원"}}],
}


def wait_until(predicate, timeout: float = 2.0) -> None:
    """백그라운드 로딩이 끝날 때까지 대기."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("시간 내에 조건이 충족되지 않음")


@pytest.fixture
def make_client():
    """make_client(agent=..., db_ok=...) → 서비스 로딩이 끝난 TestClient."""
    clients = []

    def _make(agent: FakeAgent | None = None, db_ok: bool = True, loader="fake"):
        if loader == "fake":
            app = create_app(loader=lambda: FakeServices(db_ok))
        else:
            app = create_app(loader=loader)
        if agent is not None:
            app.dependency_overrides[get_agent] = lambda: agent
        client = TestClient(app)
        client.__enter__()   # lifespan 실행
        clients.append(client)
        if loader == "fake":
            wait_until(lambda: app.state.services is not None)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
