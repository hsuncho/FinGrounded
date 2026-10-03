"""파서 라우터: 파일 확장자에 따라 알맞은 파서로 분기.

반환 형식은 파서 종류와 무관하게 통일: [{'locator': str, 'text': str}, ...]
locator는 출처 세부위치(PDF=페이지, XLSX=시트)로, 인용 표기에 사용된다.
새 형식(DOCX/PPTX/이미지)은 여기에 분기만 추가하면 확장된다.
"""
from __future__ import annotations

import os

from .pdf_parser import parse_pdf
from .xlsx_parser import parse_xlsx

SUPPORTED = {".pdf", ".xlsx", ".xlsm"}


def parse_file(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return [{"locator": f"p.{p['page']}", "text": p["text"]} for p in parse_pdf(path)]
    if ext in (".xlsx", ".xlsm"):
        return [{"locator": f"sheet:{s['sheet']}", "text": s["text"]} for s in parse_xlsx(path)]
    raise ValueError(f"지원하지 않는 형식: {ext} ({path})")
