from __future__ import annotations

import json

from dotenv import load_dotenv

from embeddings import Embedder
from ingest import db
from llm import LLM
from agent import Agent

QUESTIONS = [
    "삼성전자 2023년 부채비율은 얼마야?",              # 수치형
    "2023년 반도체 기업들의 부채비율을 비교해줘.",      # 비교형
    "삼성전자 2023년 영업이익률은? (매출액 표기가 영업수익임)",  # 계정 별칭 처리
    "삼성전자 2019년 부채비율은?",                      # 데이터 없음 → 거부 기대
]


def main() -> None:
    load_dotenv()
    conn = db.get_conn()
    db.register_pgvector(conn)
    embedder = Embedder()
    agent = Agent(conn, embedder, LLM())

    for q in QUESTIONS:
        print("=" * 64)
        print("Q:", q)
        ans = agent.run(q)
        print(json.dumps(ans, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
