"""청킹 유틸: 문자 기준 슬라이딩 윈도우(겹침 포함).

한국어 공시문서용 MVP 구현. 개선안: kss로 문장 분리 후 문장 단위 패킹.
"""
from __future__ import annotations


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks
