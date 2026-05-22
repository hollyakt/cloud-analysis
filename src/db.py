"""Local SQLite schema for NIH RePORTER project records."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reporter.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_num         TEXT PRIMARY KEY,
    fiscal_year         INTEGER,
    title               TEXT,
    award_amount        REAL,
    org_name            TEXT,
    org_state           TEXT,
    org_country         TEXT,
    agency_ic_code      TEXT,
    agency_ic_name      TEXT,
    project_start_date  TEXT,
    project_end_date    TEXT,
    pi_first            TEXT,
    pi_last             TEXT,
    terms               TEXT,            -- raw "<term1><term2>..." blob from API
    fetched_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_projects_year   ON projects(fiscal_year);
CREATE INDEX IF NOT EXISTS ix_projects_org    ON projects(org_name);
CREATE INDEX IF NOT EXISTS ix_projects_agency ON projects(agency_ic_code);
"""


def init_db(path: Path = DB_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
    return path


@contextmanager
def connect(path: Path = DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    print("Initialized", init_db())
