"""FRED API 클라이언트 (거시 시계열 조회)."""
from __future__ import annotations

import requests

BASE = "https://api.stlouisfed.org/fred"


class FredError(RuntimeError):
    pass


class FredClient:
    def __init__(self, api_key: str, timeout: int = 20):
        if not api_key:
            raise FredError("FRED_API_KEY가 비어 있습니다.")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

    def series_info(self, series_id: str) -> dict:
        """시계열 메타(제목·단위 등) 조회."""
        resp = self._session.get(
            f"{BASE}/series",
            params={"series_id": series_id, "api_key": self.api_key, "file_type": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        seriess = resp.json().get("seriess", [])
        return seriess[0] if seriess else {}

    def observations(self, series_id: str, start: str) -> list[dict]:
        """관측값 리스트 조회. 값이 '.'이면 결측이므로 후처리 필요."""
        resp = self._session.get(
            f"{BASE}/series/observations",
            params={
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("observations", [])
