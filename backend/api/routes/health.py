"""상태 확인 엔드포인트.
- /healthz (liveness): 프로세스가 살아서 요청을 받는가. 모델 로딩 중에도 200.
  로딩이 실패했다면 이 프로세스는 회복할 수 없으므로 503 → 재시작 대상.
- /readyz (readiness): 실제 질문을 처리할 수 있는가. 모델 로딩 완료 + DB 쿼리 성공이어야 200.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger("fingrounded.api")


@router.get("/healthz")
def healthz(request: Request):
    if getattr(request.app.state, "load_error", None):
        return JSONResponse(status_code=503, content={"status": "failed"})
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request):
    services = getattr(request.app.state, "services", None)
    if services is None:
        return JSONResponse(status_code=503, content={"status": "loading"})
    try:
        services.check_db()
    except Exception:
        logger.warning("readiness: DB 확인 실패", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "db_unavailable"})
    return {"status": "ready"}
