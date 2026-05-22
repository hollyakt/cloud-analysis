"""Fetch NIH-funded project records from the public NIH RePORTER REST API.

API docs: https://api.reporter.nih.gov/
No authentication required.
"""
from __future__ import annotations

import argparse
import time
from typing import Iterable

import requests

from db import connect, init_db

ENDPOINT = "https://api.reporter.nih.gov/v2/projects/search"
INCLUDE = [
    "ProjectNum", "ProjectTitle", "FiscalYear", "AwardAmount",
    "Organization", "AgencyIcAdmin",
    "ProjectStartDate", "ProjectEndDate",
    "PrincipalInvestigators", "Terms",
]


def _payload(fiscal_years: list[int], offset: int, limit: int,
             agency: str | None) -> dict:
    criteria: dict = {"fiscal_years": fiscal_years}
    if agency:
        criteria["agencies"] = [agency]
    return {
        "criteria": criteria,
        "include_fields": INCLUDE,
        "offset": offset,
        "limit": limit,
    }


def fetch_page(fiscal_years: list[int], offset: int, limit: int,
               agency: str | None) -> tuple[list[dict], int]:
    body = _payload(fiscal_years, offset, limit, agency)
    r = requests.post(ENDPOINT, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["results"], int(data["meta"].get("total", 0))


def _flatten(rec: dict) -> dict:
    pis = rec.get("principal_investigators") or []
    contact = next((p for p in pis if p.get("is_contact_pi")), pis[0] if pis else {})
    org = rec.get("organization") or {}
    agency = rec.get("agency_ic_admin") or {}
    return {
        "project_num": rec.get("project_num"),
        "fiscal_year": rec.get("fiscal_year"),
        "title": rec.get("project_title"),
        "award_amount": rec.get("award_amount"),
        "org_name": org.get("org_name"),
        "org_state": org.get("org_state"),
        "org_country": org.get("org_country"),
        "agency_ic_code": agency.get("code"),
        "agency_ic_name": agency.get("name"),
        "project_start_date": rec.get("project_start_date"),
        "project_end_date": rec.get("project_end_date"),
        "pi_first": (contact.get("first_name") or "").strip(),
        "pi_last": (contact.get("last_name") or "").strip(),
        "terms": rec.get("terms"),
    }


def upsert(rows: Iterable[dict]) -> int:
    rows = [r for r in rows if r.get("project_num")]
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT OR REPLACE INTO projects ({','.join(cols)}) VALUES ({placeholders})"
    with connect() as conn:
        conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
    return len(rows)


def fetch(fiscal_years: list[int], agency: str | None = "NIH",
          limit: int = 500, max_records: int = 5000) -> int:
    init_db()
    total_loaded = 0
    offset = 0
    while total_loaded < max_records:
        page_limit = min(limit, max_records - total_loaded)
        results, total_available = fetch_page(fiscal_years, offset, page_limit, agency)
        if not results:
            break
        flattened = [_flatten(r) for r in results]
        n = upsert(flattened)
        total_loaded += n
        print(f"  offset {offset}: stored {n} (cumulative {total_loaded}, "
              f"api total {total_available})")
        if offset + page_limit >= total_available:
            break
        offset += page_limit
        time.sleep(0.3)   # be polite
    return total_loaded


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=[2020, 2021, 2022, 2023])
    ap.add_argument("--agency", default="NIH")
    ap.add_argument("--max-records", type=int, default=2000)
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()
    n = fetch(args.years, agency=args.agency,
              limit=args.limit, max_records=args.max_records)
    print(f"Done. Stored {n} projects.")


if __name__ == "__main__":
    main()
