"""XLSX 파서: 시트 단위로 행을 텍스트화(시트명 = 출처 위치)."""
from __future__ import annotations

import openpyxl


def parse_xlsx(path: str) -> list[dict]:
    """[{'sheet': str, 'text': str}, ...] 반환."""
    out = []
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            lines = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    lines.append(" | ".join(cells))
            if lines:
                out.append({"sheet": ws.title, "text": "\n".join(lines)})
    finally:
        wb.close()
    return out
