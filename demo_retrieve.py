# 검색 데모: 몇 가지 질의로 top-k 청크와 출처를 출력.
from __future__ import annotations

from dotenv import load_dotenv

from embeddings import Embedder
from ingest import db
from retriever import search

QUERIES = [
    "삼성전자 2023년 부채총계와 자본총계는?",
    "카카오 영업이익",
    "반도체 기업 매출액",
]


def main() -> None:
    load_dotenv()
    conn = db.get_conn()
    db.register_pgvector(conn)
    embedder = Embedder()

    for q in QUERIES:
        print("=" * 64)
        print("Q:", q)
        for r in search(conn, embedder, q, k=3):
            cite = r["title"] + (f" · {r['locator']}" if r["locator"] else "")
            print(f"  [{r['score']:.3f}] {cite}")
            print(f"        {r['content'][:90].replace(chr(10), ' ')}...")
    conn.close()


if __name__ == "__main__":
    main()
