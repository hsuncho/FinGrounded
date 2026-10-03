"""PostgreSQL 연결 및 upsert 헬퍼."""
from __future__ import annotations

import os

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json


def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL이 설정되어 있지 않습니다(.env 확인).")
    return psycopg2.connect(dsn)


def register_pgvector(conn):
    """psycopg2 커넥션에 vector 타입 어댑터 등록(스키마 적용 이후 호출)."""
    from pgvector.psycopg2 import register_vector

    register_vector(conn)


def apply_schema(conn, schema_path: str = "sql/schema.sql") -> None:
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def upsert_company(conn, corp_code, corp_name, stock_code, industry) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO companies (corp_code, corp_name, stock_code, industry)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (corp_code) DO UPDATE
              SET corp_name = EXCLUDED.corp_name,
                  stock_code = EXCLUDED.stock_code,
                  industry = EXCLUDED.industry
            """,
            (corp_code, corp_name, stock_code, industry),
        )
    conn.commit()


def upsert_financial_facts(conn, records: list[tuple]) -> int:
    """records: (corp_code,bsns_year,reprt_code,fs_div,sj_div,sj_nm,
    account_id,account_nm,account_detail,amount,prev_amount,currency,ord,source_url)"""
    if not records:
        return 0
    sql = """
        INSERT INTO financial_facts
          (corp_code, bsns_year, reprt_code, fs_div, sj_div, sj_nm,
           account_id, account_nm, account_detail, amount, prev_amount, currency, ord, source_url)
        VALUES %s
        ON CONFLICT (corp_code, bsns_year, reprt_code, fs_div, sj_div, account_id, account_nm, account_detail, ord)
        DO UPDATE SET amount = EXCLUDED.amount,
                      prev_amount = EXCLUDED.prev_amount,
                      currency = EXCLUDED.currency,
                      source_url = EXCLUDED.source_url,
                      sj_nm = EXCLUDED.sj_nm
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, records)
    conn.commit()
    return len(records)


# ---- 문서/청크 적재 ----
def upsert_document(conn, doc: dict) -> None:
    """doc keys: doc_id, source_type, corp_code, period, title, url"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (doc_id, source_type, corp_code, period, title, url, raw_text)
            VALUES (%(doc_id)s, %(source_type)s, %(corp_code)s, %(period)s,
                    %(title)s, %(url)s, NULL)
            ON CONFLICT (doc_id) DO UPDATE
              SET source_type = EXCLUDED.source_type,
                  corp_code = EXCLUDED.corp_code,
                  period = EXCLUDED.period,
                  title = EXCLUDED.title,
                  url = EXCLUDED.url
            """,
            doc,
        )
    conn.commit()


def delete_chunks(conn, doc_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))
    conn.commit()


def insert_chunks(conn, records: list[tuple]) -> int:
    """records: (doc_id, chunk_index, content, embedding(np.ndarray), meta(dict))
    register_pgvector가 선행되어야 numpy 배열이 vector로 적재된다."""
    if not records:
        return 0
    values = [(r[0], r[1], r[2], r[3], Json(r[4])) for r in records]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO document_chunks (doc_id, chunk_index, content, embedding, meta) VALUES %s",
            values,
            template="(%s, %s, %s, %s, %s)",
        )
    conn.commit()
    return len(records)


def upsert_macro(conn, records: list[tuple]) -> int:
    """records: (series_id, obs_date, value, title, units)"""
    if not records:
        return 0
    sql = """
        INSERT INTO macro_series (series_id, obs_date, value, title, units)
        VALUES %s
        ON CONFLICT (series_id, obs_date)
        DO UPDATE SET value = EXCLUDED.value,
                      title = EXCLUDED.title,
                      units = EXCLUDED.units
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, records)
    conn.commit()
    return len(records)
