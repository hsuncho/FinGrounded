# FinGrounded

DART(공시·재무) + FRED(거시경제)를 수집·정규화하여 PostgreSQL에 적재

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
- `documents`/`document_chunks` — (멀티모달 파싱·임베딩)에서 채움. pgvector 컬럼 포함

## 멀티모달 파싱 + RAG 검색

정형 재무데이터로부터 요약 사실문서를 생성하고(항상 동작), `data/docs/`에 넣은
PDF·XLSX도 파싱하여 KURE-v1로 임베딩·인덱싱한 뒤 출처 달린 검색을 제공한다.

```bash
python ingest_docs.py                      # 사실문서 + data/docs/ 파일 → 청킹·임베딩·적재
python demo_retrieve.py                    # 검색 데모(질의 → top-k 청크 + 출처)
```

- 멀티모달 확장: `data/docs/`에 DART에서 받은 사업보고서 PDF나 재무 XLSX를
  넣고 `ingest_docs.py`를 다시 실행하면 자동으로 파싱·인덱싱된다.
- 임베딩 모델 교체: `embeddings.Embedder(model_name="BAAI/bge-m3")` 처럼 바꾸면
  된다(둘 다 1024차원).

### 검색 인덱스
```sql
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

- 재무비율 계산 도구 + 도구호출 Agent, 구조화 JSON 출력
- 골든 테스트셋 + 평가 러너 + pytest 회귀 게이트

## 도구호출 Agent + 구조화 출력

RAG·계산 도구를 붙여, 질문을 분석해 도구를 호출하고 출처 달린 구조화 JSON으로 답한다.

```bash
python demo_agent.py     # 수치형·비교형·거부형 질문 실행
```

### 도구 구성
- `calculate_financial_ratio(company, year, ratio)` — 부채비율/유동비율/ROE/영업이익률/순이익률을
  DB 정형데이터로 **결정적 계산**(숫자 환각 차단). 계정명 흔들림은 별칭으로 흡수.
- `compare_by_industry(industry, metric, year)` — 산업 필터로 동종업계를 **전부** 계산·정렬
  (RAG 랭킹 쏠림 문제를 구조로 회피).
- `search_knowledge_base(query, k)` — 서술형 근거 RAG 검색.

### 핵심 설계
- **출처는 LLM이 아니라 시스템이 채운다**: 실제 실행된 도구 결과에서 sources를 수집해
  최종 JSON에 주입 → 인용 환각을 구조적으로 차단.
- 최종 출력: `{answer, confidence, caveats, sources[], tool_calls[]}`.