"""임베딩 모델 래퍼.

기본은 KURE-v1(한국어 검색 특화, BGE-m3 기반, 1024차원).
model_name만 바꾸면 BGE-m3 등으로 교체 가능
"""
from __future__ import annotations

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "nlpai-lab/KURE-v1"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]):
        """정규화된 임베딩(numpy)을 반환. cosine 검색(<=>)과 짝을 이룬다."""
        return self.model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
