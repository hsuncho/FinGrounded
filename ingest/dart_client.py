"""OpenDART API 클라이언트 (고유번호 매핑 + 단일회사 전체 재무제표)."""
from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET

import requests

BASE = "https://opendart.fss.or.kr/api"


class OpenDartError(RuntimeError):
    pass


class OpenDartClient:
    def __init__(self, api_key: str, timeout: int = 20):
        if not api_key:
            raise OpenDartError("OPENDART_API_KEY가 비어 있습니다.")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

    # ---- 고유번호(corp_code) 매핑 ----
    def fetch_corp_code_map(self) -> dict[str, str]:
        """corpCode.xml(ZIP)을 내려받아 {종목코드: 고유번호} 매핑을 만든다.

        비상장사는 종목코드가 비어 있어 매핑에서 제외된다.
        """
        resp = self._session.get(
            f"{BASE}/corpCode.xml",
            params={"crtfc_key": self.api_key},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        # 인증 실패 등은 ZIP이 아니라 에러 XML로 오므로 방어
        if resp.content[:2] != b"PK":
            raise OpenDartError(f"corpCode 응답이 ZIP이 아님(인증키 확인): {resp.text[:200]}")
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xml_bytes = zf.read(zf.namelist()[0])
        root = ET.fromstring(xml_bytes)
        mapping: dict[str, str] = {}
        for node in root.iter("list"):
            stock = (node.findtext("stock_code") or "").strip()
            corp = (node.findtext("corp_code") or "").strip()
            if stock and corp:
                mapping[stock] = corp
        return mapping

    # ---- 단일회사 전체 재무제표 ----
    def fetch_full_financials(
        self, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str
    ) -> list[dict]:
        """fnlttSinglAcntAll: BS/IS/CIS/CF 등 전체 재무제표 계정 리스트 반환.

        status '000' 성공, '013' 데이터 없음(빈 리스트 반환), 그 외는 예외.
        """
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }
        resp = self._session.get(
            f"{BASE}/fnlttSinglAcntAll.json", params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "013":  # 조회된 데이터 없음
            return []
        if status != "000":
            raise OpenDartError(f"OpenDART 오류 status={status} msg={data.get('message')}")
        return data.get("list", [])
