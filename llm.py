from __future__ import annotations

import os

from anthropic import Anthropic


class LLM:
    def __init__(self, model: str | None = None):
        self.client = Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    def create(self, system, messages, tools, max_tokens: int = 1024):
        return self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )
