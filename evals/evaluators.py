"""평가용 순수 함수(스코어러). DB·API 없이 동작 → 단위 테스트로 항상 검증 가능.

여기 있는 함수는 '문자열/숫자 판정' 로직만 담는다. 정답(ground truth)을
도구로 계산하는 일은 run_eval에서 하고, 그 값을 이 함수들에 넘긴다.
"""
from __future__ import annotations

import re

# 콤마 포함 정수/소수 추출 (예: "25.36", "92,228,115", "2.54%")
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")

# 데이터 부재를 알리는 거부 표현
_REFUSAL_MARKERS = (
    "찾을 수 없", "없습니다", "등록되어 있지 않", "데이터가 없",
    "확인할 수 없", "제공할 수 없", "알 수 없", "존재하지 않",
)


def extract_numbers(text: str) -> list[float]:
    out: list[float] = []
    for m in _NUM.findall(text or ""):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def numeric_match(answer: str, expected: float, tol: float = 0.5) -> bool:
    """답변 안에 기대값과 tol 이내로 일치하는 숫자가 있는가(백분율 오차 아님, 절대 %p)."""
    return any(abs(n - expected) <= tol for n in extract_numbers(answer))


def is_refusal(answer: str, sources: list) -> bool:
    """출처가 비어 있고 거부 표현이 있으면 정직한 거부로 본다."""
    has_marker = any(m in (answer or "") for m in _REFUSAL_MARKERS)
    return has_marker and not sources


def has_grounding(answer: str, sources: list) -> bool:
    """비거부 답변은 출처가 최소 1개 있어야 근거 있음으로 본다."""
    return bool(sources) and bool((answer or "").strip())


def contains_all(answer: str, names: list[str]) -> bool:
    """비교 답변에 기대 기업명이 모두 등장하는가."""
    a = answer or ""
    return all(n in a for n in names)
