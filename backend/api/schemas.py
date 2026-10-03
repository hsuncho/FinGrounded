from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_QUESTION_LEN = 500

Confidence = Literal["high", "medium", "low"]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LEN)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("질문이 비어 있습니다.")
        return v


class Source(BaseModel):
    title: str
    url: str | None = None
    locator: str | None = None


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = {}
    ok: bool | None = None


class ComputedValue(BaseModel):
    """calculate_financial_ratio가 DB 계정 값으로 계산한 결과"""
    company: str
    year: str
    ratio: str
    value: float
    unit: str
    inputs: dict[str, str]

    @field_validator("year", mode="before")
    @classmethod
    def year_to_str(cls, v: Any) -> str:
        return str(v)


class AskResponse(BaseModel):
    answer: str
    confidence: Confidence
    caveats: str = ""
    sources: list[Source] = []
    tool_calls: list[ToolCall] = []
    computed: list[ComputedValue] = []


def to_response(raw: dict) -> AskResponse:
    """Agent 출력(dict)을 응답 스키마로 변환.

    answer·confidence·caveats는 LLM이 쓴 JSON이라 형식이 어긋날 수 있다.
    어긋난 값은 실패로 처리하지 않고 보수적인 값(low 등)으로 맞춘다.
    sources·tool_calls·computed는 시스템이 채운 값이라 그대로 검증한다.
    """
    confidence = raw.get("confidence")
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    return AskResponse(
        answer=str(raw.get("answer") or ""),
        confidence=confidence,
        caveats=str(raw.get("caveats") or ""),
        sources=raw.get("sources", []),
        tool_calls=raw.get("tool_calls", []),
        computed=raw.get("computed", []),
    )
