# FinGrounded

**근거 기반 재무 질의응답 Agent**

한국 상장기업의 공시·재무 데이터(DART)와 거시경제 지표(FRED)를 지식베이스로 삼아, 재무 질문에 **출처가 달린 구조화된 답변**을 내는 LLM Agent입니다. 재무 수치는 LLM이 생성하지 않고 전용 계산 도구가 DB 데이터로 계산하며, 답변의 출처는 실제로 실행된 도구 결과에서 시스템이 수집합니다.

```text
Q. 삼성전자 2023년 부채비율은 얼마야?
A. 삼성전자의 2023년 부채비율은 25.36%입니다.
   (부채총계 92조 2,281억 원 ÷ 자본총계 363조 6,779억 원)
   출처: 삼성전자 2023 연결재무제표 (OpenDART fnlttSinglAcntAll)
```

---

## 왜 만들었나

범용 LLM에 재무 질문을 하면 그럴듯한 숫자를 만들어내거나, 확인할 수 없는 출처를 제시하는 경우가 있습니다. 회계·재무처럼 수치 하나가 중요한 영역에서는 **정확성과 근거를 구조로 보장**해야 한다고 보고, 다음 원칙으로 설계했습니다.

| 원칙 | 구현 |
|---|---|
| 수치는 계산하고 생성하지 않는다 | 재무비율은 DB의 계정 값으로 결정적으로 계산하는 도구가 담당 |
| 출처는 LLM이 쓰지 않는다 | 실행된 도구 결과에서 출처를 수집해 최종 응답에 주입 |
| 모르면 모른다고 답한다 | 데이터가 없으면 추정하지 않고 거부. 거부 여부를 평가 항목으로 검증 |
| 품질은 수치로 관리한다 | 골든 테스트셋 + 지표 + pytest 회귀 게이트 |

---

## 아키텍처

```text
[지식베이스 구축]
 OpenDART API ─┐                               ┌─ financial_facts (계정 단위 재무 데이터)
 FRED API ─────┼─► 수집·정규화 ─► PostgreSQL ──┼─ macro_series (거시 시계열)
 PDF / XLSX ───┘   (출처 메타 부착)            └─ document_chunks (KURE 임베딩, pgvector)

[질의응답]
 질문 ─► LLM Agent ─► 도구 선택·호출 ─► 결과 관찰 ─► 구조화 JSON 답변
                        ├ calculate_financial_ratio  재무비율 계산
                        ├ compare_by_industry        동종업계 비교
                        └ search_knowledge_base      서술형 근거 검색 (RAG)

[품질·보안]
 골든셋 평가 + 회귀 게이트 (pytest)      SAST · SCA · 시크릿 탐지 (GitHub Actions)
```

---

## 주요 기능

### 1. 데이터 수집 파이프라인
- **OpenDART**: 대상 기업의 연결 재무제표 전체 계정(`fnlttSinglAcntAll`)을 수집합니다. 기업 고유번호는 하드코딩하지 않고 `corpCode.xml`에서 종목코드로 매핑합니다.
- **FRED**: 미국 CPI, 기준금리, 실업률, 10년물 국채금리, 원/달러 환율을 수집합니다.
- 모든 재무 데이터에 출처 API URL을 함께 저장합니다.
- 대상: 삼성전자, SK하이닉스, NAVER, 카카오, 현대차 (2022~2024 사업보고서)

### 2. 문서 파싱 + RAG 검색
- 파일 확장자에 따라 파서를 고르는 라우터 구조입니다(PDF는 페이지, XLSX는 시트 단위로 추출하고 위치를 출처로 기록).
- 정형 재무 데이터로 회사·연도별 요약 문서를 생성하고, 여기에 산업 정보를 넣어 동종업계 검색이 가능하도록 했습니다.
- 한국어 검색 특화 임베딩 [KURE-v1](https://github.com/nlpai-lab/KURE)(1024차원)과 pgvector 코사인 유사도로 검색합니다. 임베딩 모델은 교체 가능하게 분리했습니다.

### 3. 도구호출 Agent

| 도구 | 역할 |
|---|---|
| `calculate_financial_ratio(company, year, ratio)` | 부채비율·유동비율·ROE·영업이익률·순이익률 계산. 회사마다 다른 계정명 표기(`매출액`/`영업수익`/`수익(매출액)`)는 별칭으로 처리 |
| `compare_by_industry(industry, metric, year)` | 같은 산업의 모든 기업을 계산해 정렬. RAG 검색 순위가 한 회사에 쏠려 비교 대상이 빠지는 문제를 피하기 위해 분리 |
| `search_knowledge_base(query, k)` | 설명·맥락이 필요할 때 쓰는 서술형 근거 검색 |

최종 출력 형식:
```json
{
  "answer": "...",
  "confidence": "high | medium | low",
  "caveats": "...",
  "sources": [{"title": "...", "url": "...", "locator": "..."}],
  "tool_calls": [{"name": "...", "args": {}, "ok": true}]
}
```

### 4. 평가·회귀 하네스
- 골든 테스트셋 20문항(수치 8 · 비교 3 · 거부 4 · 검색 5)
- 정답을 하드코딩하지 않고, 평가 시점에 계산 도구로 정답을 구해 LLM 답변과 비교합니다. 데이터가 바뀌어도 골든셋을 고칠 필요가 없습니다.
- 스코어러(무료·결정적)는 단위 테스트로, Agent 전체 평가(API 비용 발생)는 회귀 게이트로 분리했습니다. CI에서는 단위 테스트만 매번 실행합니다.

### 5. 보안 점검 파이프라인
- **SAST**: Semgrep 공개 룰셋(`p/python`, `p/security-audit`)과 프로젝트 커스텀 룰(SQL 문자열 포매팅, 하드코딩 시크릿)
- **SCA**: pip-audit로 의존성 취약점 점검
- **시크릿 탐지**: gitleaks. push 시에는 새 커밋을, 수동 실행 시에는 전체 이력을 검사
- 탐지 결과 분석과 조치 내용, 위협 모델은 [SECURITY.md](SECURITY.md)에 정리했습니다.

---

## 평가 결과

Agent(Claude)로 골든셋 20문항을 실행한 결과입니다.

| 지표 | 결과 |
|---|---|
| 도구 선택 정확도 | 1.00 |
| 수치 정답률 (허용오차 ±0.5%p) | 1.00 |
| 근거성 (출처 존재) | 1.00 |
| 비교 정확도 | 1.00 |
| 거부 정확도 | 1.00 |
| 검색 Hit@3 | 1.00 |
| 전체 통과율 | 1.00 |

임베딩 모델 비교(검색 5문항, Hit@3)에서는 KURE-v1과 BGE-m3가 모두 1.00이었습니다.

> 현재 골든셋은 회사·연도 단위로 정답을 판정하기 때문에 난이도가 낮습니다. 만점과 임베딩 모델 간 차이 없음은 이 한계의 영향도 받습니다. 개선 방향은 아래 [한계와 향후 과제](#한계와-향후-과제)에 적었습니다.

---

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 언어 | Python 3.11+ |
| 데이터베이스 | PostgreSQL 16 + pgvector |
| 임베딩 | KURE-v1 (sentence-transformers) |
| LLM | Claude (Anthropic API, 도구 호출) |
| 문서 파싱 | PyMuPDF, openpyxl |
| 테스트·CI | pytest, GitHub Actions |
| 보안 점검 | Semgrep, pip-audit, gitleaks, defusedxml |

---

## 프로젝트 구조

```text
FinGrounded/
├── backend/
│   ├── config.py               # 대상 기업·연도·거시 시계열 정의
│   ├── ingest/                 # OpenDART·FRED 클라이언트, DB 헬퍼
│   ├── ingest_dart.py          # 재무제표 수집·적재
│   ├── ingest_fred.py          # 거시 시계열 수집·적재
│   ├── ingest_docs.py          # 문서 생성·파싱 → 청킹 → 임베딩 → 적재
│   ├── parsers/                # 확장자별 파서 라우터 (PDF, XLSX)
│   ├── chunk.py                # 청킹
│   ├── embeddings.py           # 임베딩 모델 래퍼 (교체 가능)
│   ├── retriever.py            # pgvector 검색
│   ├── tools.py                # Agent 도구 + 도구 스키마
│   ├── llm.py                  # LLM 클라이언트
│   ├── agent.py                # 도구호출 루프 + 구조화 출력
│   ├── evals/                  # 골든셋, 스코어러, 평가 러너, 임베딩 비교
│   ├── tests/                  # 단위 테스트, 회귀 게이트
│   ├── sql/schema.sql          # 테이블·pgvector 스키마
│   └── .semgrep/rules.yml      # 커스텀 SAST 룰
├── .github/workflows/      # ci.yml (테스트), security.yml (보안 점검)
└── SECURITY.md             # 보안 점검 결과·조치 기록
```

---

## 시작하기

### 1. 준비
- [OpenDART](https://opendart.fss.or.kr) 인증키
- [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) 인증키
- [Anthropic API](https://console.anthropic.com) 키
- PostgreSQL + pgvector (Docker 사용 시)
  ```bash
  docker run -d --name fg-pg -p 5432:5432 \
    -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fingrounded \
    pgvector/pgvector:pg16
  ```

### 2. 설치
```bash
cd backend                       
python -m venv .venv
source .venv/bin/activate        # Windows(Git Bash): source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env             # 키 입력
```

`.env`
```env
OPENDART_API_KEY=...
FRED_API_KEY=...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fingrounded
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=...               # 사용할 Claude 모델
```

### 3. 데이터 적재
```bash
python ingest_dart.py    # 재무제표 수집·적재 (테이블 자동 생성)
python ingest_fred.py    # 거시 시계열 수집·적재
python ingest_docs.py    # 요약 문서 생성 + data/docs/ 파일 파싱 → 임베딩 적재
```
`data/docs/`에 사업보고서 PDF나 재무 XLSX를 넣고 `ingest_docs.py`를 다시 실행하면 함께 인덱싱됩니다. 첫 실행 시 KURE 모델(약 2GB)을 내려받습니다.

### 4. 실행
```bash
python demo_retrieve.py  # 검색 데모: 질의 → 상위 청크 + 출처
python demo_agent.py     # Agent 데모: 수치형·비교형·거부형 질문
```

### 5. 평가·테스트
```bash
python -m evals.run_eval            # 골든셋 평가 → evals/report.json
python -m evals.compare_embeddings  # KURE vs BGE-m3 검색 비교
pytest tests/test_evaluators.py     # 단위 테스트 (API·DB 불필요)
pytest tests/test_regression.py     # 회귀 게이트 (API 키·DB 필요)
```

### 6. 보안 점검 (로컬)
```bash
pip install semgrep pip-audit
PYTHONUTF8=1 semgrep scan --config p/python --config p/security-audit --config .semgrep .
pip-audit -r requirements.txt
```
Windows에서는 룰 파일의 한글 메시지 때문에 `PYTHONUTF8=1`이 필요합니다.

---

## 데이터 확인 쿼리

```sql
-- 기업별 적재 건수
SELECT corp_name, count(*)
FROM financial_facts f JOIN companies c USING (corp_code)
GROUP BY corp_name;

-- 삼성전자 2023 연결 부채총계·자본총계
SELECT account_nm, amount
FROM financial_facts f JOIN companies c USING (corp_code)
WHERE c.corp_name = '삼성전자' AND bsns_year = '2023' AND sj_div = 'BS'
  AND account_nm IN ('부채총계', '자본총계');

-- 최근 미국 기준금리
SELECT obs_date, value FROM macro_series
WHERE series_id = 'FEDFUNDS' ORDER BY obs_date DESC LIMIT 5;
```

데이터가 늘어나면 벡터 인덱스를 추가할 수 있습니다.
```sql
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

---

## 한계와 향후 과제

- **평가 난이도**: 검색 정답을 회사·연도 단위로 판정합니다. 계정 위치(재무상태표·손익계산서)까지 요구하고 추론형 질의를 추가해 변별력을 높일 계획입니다.
- **검색 혼동**: "영업이익"과 "영업활동현금흐름"처럼 표면이 비슷한 계정을 혼동하는 경우를 확인했습니다. 벡터 검색과 BM25를 결합한 하이브리드 검색으로 개선할 계획입니다.
- **문서 형식**: 현재 PDF와 XLSX만 지원합니다. 라우터에 DOCX·PPTX·이미지(OCR) 파서를 추가할 수 있습니다.
- **보안 점검 범위**: 상주 API 서버가 없어 DAST는 적용하지 않았습니다. API 계층을 추가하면 OWASP ZAP을 붙일 예정입니다.
- **CI 게이트**: 보안 점검은 결과 수집 목적이라 빌드를 막지 않습니다. 운영 환경이라면 심각도 기준으로 PR을 차단하도록 바꿔야 합니다.
