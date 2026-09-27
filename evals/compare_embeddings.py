"""임베딩 모델 비교 실험: KURE-v1 vs BGE-m3 를 같은 골든셋으로 Hit@k 측정.
DB에 저장된 청크를 꺼내 두 모델로 각각 in-memory 임베딩 후 코사인 검색."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from ingest import db

MODELS = ["nlpai-lab/KURE-v1", "BAAI/bge-m3"]
GOLDEN = Path(__file__).with_name("golden_set.jsonl")
K = 3


def load_retrieval_items() -> list[dict]:
    items = []
    with open(GOLDEN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                if obj["type"] == "retrieval":
                    items.append(obj)
    return items


def load_chunks(conn):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT dc.content, d.title
               FROM document_chunks dc JOIN documents d ON d.doc_id = dc.doc_id"""
        )
        return cur.fetchall()  # [(content, title), ...]


def hit_at_k(model_name, chunks, items) -> float:
    model = SentenceTransformer(model_name)
    contents = [c for c, _ in chunks]
    titles = [t for _, t in chunks]
    doc_emb = model.encode(contents, normalize_embeddings=True, convert_to_numpy=True)

    hits = 0
    for it in items:
        q = model.encode([it["question"]], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = doc_emb @ q  # 정규화됐으므로 내적 = 코사인
        top = np.argsort(-scores)[:K]
        if any(it["expect"]["title_contains"] in titles[i] for i in top):
            hits += 1
    return round(hits / len(items), 3)


def main():
    load_dotenv()
    conn = db.get_conn()
    chunks = load_chunks(conn)
    items = load_retrieval_items()
    conn.close()
    print(f"청크 {len(chunks)}개, 검색 질의 {len(items)}개, k={K}\n")

    for m in MODELS:
        print(f"임베딩: {m} 로딩·측정 중...")
        score = hit_at_k(m, chunks, items)
        print(f"  → Hit@{K} = {score}\n")


if __name__ == "__main__":
    main()
