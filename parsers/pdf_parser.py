"""PDF 파서: 페이지 단위로 텍스트 추출(페이지 번호 = 출처 위치)."""
from __future__ import annotations

import pymupdf  # PyMuPDF (구 fitz)


def parse_pdf(path: str) -> list[dict]:
    """[{'page': int, 'text': str}, ...] 반환. 빈 페이지는 제외."""
    pages = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": i, "text": text})
    return pages
