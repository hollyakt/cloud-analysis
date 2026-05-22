"""Cloud path: load the local snapshot into BigQuery, then run the BQ-flavored
queries from sql/bq/ against it.

Auth (one-time, on your workstation):

    gcloud auth application-default login
    gcloud config set project <YOUR_PROJECT_ID>

Then:

    python src/bq.py load --project <YOUR_PROJECT_ID> --dataset reporter
    python src/bq.py query --project <YOUR_PROJECT_ID> --dataset reporter \\
                          --sql sql/bq/01_funding_by_agency_year.sql

`load` is idempotent: it overwrites the destination table on each run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from google.cloud import bigquery
except ImportError:
    print("google-cloud-bigquery is not installed. Install with:\n"
          "    pip install google-cloud-bigquery db-dtypes pyarrow", file=sys.stderr)
    raise

import pandas as pd

from db import connect

ROOT = Path(__file__).resolve().parents[1]


def load_table(project: str, dataset: str, table: str = "projects") -> int:
    """Upload the local SQLite `projects` table to BigQuery as `project.dataset.table`."""
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM projects", conn)
    df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype("Int64")
    df["award_amount"] = pd.to_numeric(df["award_amount"], errors="coerce")

    client = bigquery.Client(project=project)
    client.create_dataset(bigquery.Dataset(f"{project}.{dataset}"), exists_ok=True)

    table_ref = f"{project}.{dataset}.{table}"
    job = client.load_table_from_dataframe(
        df, table_ref,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    n = client.get_table(table_ref).num_rows
    print(f"Loaded {n} rows into {table_ref}")
    return n


def run_query(project: str, dataset: str, sql_path: Path) -> pd.DataFrame:
    """Run a sql/bq/*.sql template against {project}.{dataset}.* and return a DataFrame."""
    template = sql_path.read_text()
    rendered = template.format(project=project, dataset=dataset)
    client = bigquery.Client(project=project)
    return client.query(rendered).to_dataframe()


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    load = sub.add_parser("load", help="Load local SQLite snapshot into BigQuery")
    load.add_argument("--project", required=True)
    load.add_argument("--dataset", default="reporter")
    load.add_argument("--table", default="projects")

    query = sub.add_parser("query", help="Run a BQ-flavored SQL file against your dataset")
    query.add_argument("--project", required=True)
    query.add_argument("--dataset", default="reporter")
    query.add_argument("--sql", required=True, help="Path to sql/bq/*.sql")
    query.add_argument("--csv", help="Optional CSV output path")

    args = ap.parse_args()
    if args.cmd == "load":
        load_table(args.project, args.dataset, args.table)
    elif args.cmd == "query":
        df = run_query(args.project, args.dataset, Path(args.sql))
        print(df.head(25).to_string(index=False))
        if args.csv:
            df.to_csv(args.csv, index=False)
            print(f"Wrote {args.csv}")


if __name__ == "__main__":
    main()
