from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from agent import Agent
from api.deps import get_agent
from api.schemas import AskRequest, AskResponse, to_response

router = APIRouter()
logger = logging.getLogger("fingrounded.api")


# Agent 내부(psycopg2, Anthropic 클라이언트, 임베딩)가 모두 동기라 FastAPI가 스레드풀에서 실행하게 둔다. 
# async def로 두면 이벤트 루프가 막힌다.
@router.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, agent: Agent = Depends(get_agent)) -> AskResponse:
    try:
        raw = agent.run(req.question)
    except Exception:
        logger.exception("Agent 실행 실패")
        raise HTTPException(status_code=502, detail="답변을 생성하는 중 오류가 발생했습니다.")
    return to_response(raw)
