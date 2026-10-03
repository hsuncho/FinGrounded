"""임베딩 모델(약 2GB)은 앱 시작 시 백그라운드 스레드에서 한 번만 로드한다.
로딩 중에도 서버는 떠 있어 /healthz는 응답하고, /readyz와 /api/ask는 503을 돌려준다.
워커를 여러 개 띄우면 워커마다 모델이 메모리에 올라가므로 워커는 1개로 운영한다.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import ask, health
from api.services import Services, load_services

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("fingrounded.api")


def create_app(loader: Callable[[], Services] | None = load_services) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = None
        app.state.load_error = None

        async def _load() -> None:
            try:
                app.state.services = await asyncio.to_thread(loader)
                logger.info("서비스 로드 완료")
            except Exception as e:
                logger.exception("서비스 로드 실패")
                app.state.load_error = repr(e)

        task = asyncio.create_task(_load()) if loader else None
        yield
        if task and not task.done():
            task.cancel()
        if app.state.services is not None:
            app.state.services.close()

    app = FastAPI(title="FinGrounded API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(ask.router)
    return app


app = create_app()
