from __future__ import annotations

import os

from dotenv import load_dotenv

from config import FRED_SERIES, FRED_OBSERVATION_START
from ingest.fred_client import FredClient
from ingest import db


def parse_value(raw) -> float | None:
    if raw in (None, ".", ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def main() -> None:
    load_dotenv()
    client = FredClient(os.environ.get("FRED_API_KEY", ""))
    conn = db.get_conn()
    db.apply_schema(conn)

    total = 0
    for s in FRED_SERIES:
        info = client.series_info(s.series_id)
        title = info.get("title", s.alias)
        units = info.get("units")
        obs = client.observations(s.series_id, FRED_OBSERVATION_START)
        records = [
            (s.series_id, o["date"], parse_value(o.get("value")), title, units)
            for o in obs
        ]
        n = db.upsert_macro(conn, records)
        total += n
        print(f"  - {s.series_id} ({s.alias}): {n}건")

    print(f"완료. 총 {total}건 거시 데이터 적재.")
    conn.close()


if __name__ == "__main__":
    main()
