from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class Services:
    pool: Any       # psycopg2 ThreadedConnectionPool (getconn / putconn)
    embedder: Any   # embeddings.Embedder
    llm: Any        # llm.LLM

    def check_db(self) -> None:
        """DB에 실제로 쿼리가 나가는지 확인(readiness용). 실패하면 예외."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.rollback()
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()


def load_services() -> Services:
    from dotenv import load_dotenv
    from psycopg2.pool import ThreadedConnectionPool

    from embeddings import Embedder
    from ingest import db
    from llm import LLM

    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL이 설정되어 있지 않습니다(.env 확인).")

    class VectorPool(ThreadedConnectionPool):
        """새 연결을 만들 때마다 pgvector 타입 어댑터를 등록하는 풀."""

        def _connect(self, key=None):
            conn = super()._connect(key)
            db.register_pgvector(conn)
            return conn

    # psycopg2 풀은 반납된 연결 중 minconn개까지만 보관하고 나머지는 닫는다.
    # minconn을 작게 두면 동시 요청마다 연결을 새로 맺게 되므로 고정 크기로 운영한다.
    size = int(os.environ.get("DB_POOL_SIZE", "5"))
    pool = VectorPool(minconn=size, maxconn=size, dsn=dsn)
    return Services(pool=pool, embedder=Embedder(), llm=LLM())
