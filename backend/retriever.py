"""RAG 검색기: 질의를 임베딩하여 pgvector 코사인 유사도로 top-k 청크 검색.
각 결과에 출처(문서 제목·위치·URL)를 함께 반환
"""
from __future__ import annotations


SEARCH_SQL = """
    SELECT d.title, d.url, d.source_type, dc.meta, dc.content,
           1 - (dc.embedding <=> %s) AS score
    FROM document_chunks dc
    JOIN documents d ON d.doc_id = dc.doc_id
    ORDER BY dc.embedding <=> %s
    LIMIT %s
"""


def search(conn, embedder, query: str, k: int = 5) -> list[dict]:
    qvec = embedder.encode([query])[0]
    with conn.cursor() as cur:
        cur.execute(SEARCH_SQL, (qvec, qvec, k))
        rows = cur.fetchall()

    results = []
    for title, url, source_type, meta, content, score in rows:
        results.append({
            "title": title,
            "url": url,
            "source_type": source_type,
            "locator": (meta or {}).get("locator"),
            "content": content,
            "score": float(score),
        })
    return results
