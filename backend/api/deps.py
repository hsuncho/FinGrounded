"""라우트에 주입하는 의존성. 테스트에서는 app.dependency_overrides로 교체."""
from __future__ import annotations

import logging
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request

from agent import Agent
from api.services import Services

logger = logging.getLogger("fingrounded.api")


def get_services(request: Request) -> Services:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=503, detail="서비스를 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    return services


def get_agent(services: Services = Depends(get_services)) -> Iterator[Agent]:
    """요청마다 풀에서 연결을 빌려 Agent를 만들고, 끝나면 반납.

    psycopg2 연결은 동시에 여러 스레드가 쓰면 안 되므로 요청 단위로 분리.
    ThreadedConnectionPool은 연결이 모두 사용 중이면 기다리지 않고 예외를 던지므로 503으로 응답.
    """
    try:
        conn = services.pool.getconn()
    except Exception:
        logger.warning("DB 연결 풀 고갈 또는 연결 실패", exc_info=True)
        raise HTTPException(status_code=503, detail="요청이 많아 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.")

    try:
        yield Agent(conn, services.embedder, services.llm)
    finally:
        # 읽기 전용이어도 psycopg2는 트랜잭션을 열어 둔다. 
        # 반납 전에 정리하고, 정리조차 안 되는 연결은 풀에 돌려보내지 않고 닫는다.
        broken = bool(getattr(conn, "closed", 0))
        if not broken:
            try:
                conn.rollback()
            except Exception:
                broken = True
        services.pool.putconn(conn, close=broken)
