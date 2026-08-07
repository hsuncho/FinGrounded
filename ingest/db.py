"""PostgreSQL 연결 및 upsert 헬퍼."""
from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL이 설정되어 있지 않습니다(.env 확인).")
    return psycopg2.connect(dsn)


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
