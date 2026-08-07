"""프로젝트 설정: 지식베이스로 삼을 대상 기업과 거시 시계열 정의.

corp_code(DART 고유번호)는 여기 하드코딩하지 않는다. 종목코드만 두고,
실행 시 corpCode.xml에서 {종목코드 -> 고유번호}로 해석한다(오타/변경 방지).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    name: str
    stock_code: str   # 6자리 종목코드
    industry: str     # 동종업계 비교용 산업 그룹


# 대형주 5개 — 반도체·인터넷 동종 2쌍 + 자동차 1 (동종/이종 비교 질의 모두 커버)
COMPANIES = [
    Company("삼성전자", "005930", "반도체"),
    Company("SK하이닉스", "000660", "반도체"),
    Company("NAVER", "035420", "인터넷"),
    Company("카카오", "035720", "인터넷"),
    Company("현대차", "005380", "자동차"),
]

# 수집 대상 사업연도 / 보고서 코드 / 재무제표 구분
BSNS_YEARS = ["2022", "2023", "2024"]
REPRT_CODE = "11011"   # 11011=사업보고서(연간), 11012=반기, 11013=1분기, 11014=3분기
FS_DIV = "CFS"         # CFS=연결, OFS=별도


@dataclass(frozen=True)
class FredSeries:
    series_id: str
    alias: str


FRED_SERIES = [
    FredSeries("CPIAUCSL", "미국 소비자물가지수(CPI)"),
    FredSeries("FEDFUNDS", "미국 기준금리"),
    FredSeries("UNRATE", "미국 실업률"),
    FredSeries("DGS10", "미국 10년물 국채금리"),
    FredSeries("DEXKOUS", "원/달러 환율"),
]

FRED_OBSERVATION_START = "2015-01-01"
