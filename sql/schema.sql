-- FinGrounded 스키마
-- pgvector 확장이 설치돼 있어야 함(로컬 설치 또는 pgvector/pgvector 도커 이미지)
CREATE EXTENSION IF NOT EXISTS vector;

-- 대상 기업
CREATE TABLE IF NOT EXISTS companies (
    corp_code  TEXT PRIMARY KEY,   -- DART 고유번호(8자리)
    corp_name  TEXT NOT NULL,
    stock_code TEXT,
    industry   TEXT
);

-- 정형 재무 데이터 (fnlttSinglAcntAll 결과 정규화)
-- account_detail: SCE(자본변동표)에서 동일 account_id/account_nm이 지배기업지분/
--   비지배지분/합계 등 서로 다른 자본항목을 가리킬 때 이를 구분하는 DART 원본 필드.
-- ord: 표준계정코드가 없는 커스텀 계정(account_id가 플레이스홀더인 경우, account_detail도
--   비어있음)에서 유동/비유동처럼 실제로는 다른 계정인데 이름이 같은 경우를 구분하는 유일한 값.
-- 두 필드를 키에서 빼면 서로 다른 데이터가 같은 키로 충돌해 upsert 시 조용히 유실된다.
CREATE TABLE IF NOT EXISTS financial_facts (
    id             BIGSERIAL PRIMARY KEY,
    corp_code      TEXT NOT NULL REFERENCES companies(corp_code),
    bsns_year      TEXT NOT NULL,
    reprt_code     TEXT NOT NULL,
    fs_div         TEXT NOT NULL,      -- CFS/OFS
    sj_div         TEXT NOT NULL DEFAULT '',  -- BS/IS/CIS/CF/SCE
    sj_nm          TEXT,
    account_id     TEXT NOT NULL DEFAULT '',
    account_nm     TEXT NOT NULL DEFAULT '',
    account_detail TEXT NOT NULL DEFAULT '',
    amount         NUMERIC,           -- 당기금액
    prev_amount    NUMERIC,           -- 전기금액
    currency       TEXT,
    ord            INT,
    source_url     TEXT,
    UNIQUE (corp_code, bsns_year, reprt_code, fs_div, sj_div, account_id, account_nm, account_detail, ord)
);
CREATE INDEX IF NOT EXISTS idx_ff_company_year ON financial_facts (corp_code, bsns_year);
CREATE INDEX IF NOT EXISTS idx_ff_account ON financial_facts (account_nm);

-- 거시 시계열 (FRED)
CREATE TABLE IF NOT EXISTS macro_series (
    series_id TEXT NOT NULL,
    obs_date  DATE NOT NULL,
    value     NUMERIC,
    title     TEXT,
    units     TEXT,
    PRIMARY KEY (series_id, obs_date)
);

-- RAG용 문서/청크 (스키마만 미리 선반영)
CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    source_type TEXT,             -- dart_fs / dart_pdf / fred ...
    corp_code   TEXT,
    period      TEXT,
    title       TEXT,
    url         TEXT,
    raw_text    TEXT
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      TEXT REFERENCES documents(doc_id),
    chunk_index INT,
    content     TEXT,
    embedding   vector(1024),     -- 임베딩 차원은 사용 모델에 맞춰 조정(BGE-m3=1024)
    meta        JSONB
);
