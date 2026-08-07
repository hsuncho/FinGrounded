# FinGrounded

DART(공시·재무) + FRED(거시경제)를 수집·정규화하여 PostgreSQL에 적재하는 단계.

## 1. 사전 준비
- OpenDART 인증키: https://opendart.fss.or.kr
- FRED 인증키: https://fred.stlouisfed.org/docs/api/api_key.html
- PostgreSQL + pgvector
    ```bash
    docker run -d --name fg-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fingrounded pgvector/pgvector:pg16
    ```

## 2. 설치
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
```

## 3. 실행
```bash
python ingest_dart.py   # 5개사 x 3개년 재무제표 수집·적재
python ingest_fred.py   # 거시 시계열 5종 수집·적재
```

## 4. 검증 쿼리
```sql
-- 적재 현황
SELECT corp_name, count(*) FROM financial_facts f
JOIN companies c USING (corp_code) GROUP BY corp_name;

-- 삼성전자 2023 연결 부채총계/자본총계 (부채비율 계산 재료)
SELECT account_nm, amount FROM financial_facts f
JOIN companies c USING (corp_code)
WHERE c.corp_name='삼성전자' AND bsns_year='2023' AND sj_div='BS'
  AND account_nm IN ('부채총계','자본총계');

-- 최근 기준금리
SELECT obs_date, value FROM macro_series
WHERE series_id='FEDFUNDS' ORDER BY obs_date DESC LIMIT 5;
```

## 5. 데이터 구조
- `companies` — 대상 기업(고유번호/종목코드/산업)
- `financial_facts` — 계정 단위 정형 재무 데이터. `sj_div`로 BS/IS/CF 구분, `source_url`에 출처 API 링크
- `macro_series` — FRED 시계열
- `documents`/`document_chunks` — Day2(멀티모달 파싱·임베딩)에서 채움. pgvector 컬럼 포함

## 다음 단계
- 사업보고서 PDF·XLSX 파싱 → `documents`/`document_chunks` 적재
- 임베딩 인덱싱 → 출처 달린 RAG 답변