"""Local analysis layer.

Runs over the SQLite snapshot produced by src/fetch.py. The same analytical
questions are encoded in BigQuery flavor under sql/bq/ and identical-result
SQLite flavor under sql/sqlite/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from db import connect

RESULTS = Path(__file__).resolve().parents[1] / "results"
SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "sqlite"


def _run(name: str) -> pd.DataFrame:
    sql = (SQL_DIR / name).read_text()
    with connect() as conn:
        return pd.read_sql(sql, conn)


def funding_by_year(save: bool = True) -> pd.DataFrame:
    df = _run("01_funding_by_agency_year.sql")
    if save:
        (RESULTS / "funding_by_agency_year.csv").write_text(df.to_csv(index=False))
        pivot = df.pivot_table(index="fiscal_year", columns="agency_ic_code",
                               values="total_award_millions", aggfunc="sum").fillna(0)
        top = pivot.sum().sort_values(ascending=False).head(6).index
        pivot = pivot[top]
        ax = pivot.plot(kind="bar", stacked=True, figsize=(9, 5))
        ax.set_ylabel("Total award ($M)")
        ax.set_title("NIH funding by IC by year (top 6 ICs)")
        plt.tight_layout()
        plt.savefig(RESULTS / "funding_by_agency_year.png", dpi=120)
        plt.close()
    return df


def top_institutions(save: bool = True) -> pd.DataFrame:
    df = _run("02_top_institutions.sql")
    if save:
        (RESULTS / "top_institutions.csv").write_text(df.to_csv(index=False))
        top15 = df.head(15)
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(top15["org_name"][::-1], top15["total_award_millions"][::-1])
        ax.set_xlabel("Total award ($M)")
        ax.set_title("Top 15 institutions by NIH funding (in sample)")
        plt.tight_layout()
        plt.savefig(RESULTS / "top_institutions.png", dpi=120)
        plt.close()
    return df


def state_concentration(save: bool = True) -> pd.DataFrame:
    df = _run("03_state_concentration.sql")
    if save:
        (RESULTS / "state_concentration.csv").write_text(df.to_csv(index=False))
    return df


def summary_stats() -> dict:
    with connect() as conn:
        df = pd.read_sql(
            """SELECT COUNT(*) AS n_projects,
                      ROUND(SUM(award_amount)/1e6, 1)        AS total_award_m,
                      ROUND(AVG(award_amount), 0)            AS mean_award,
                      ROUND(MIN(fiscal_year), 0)             AS min_fy,
                      ROUND(MAX(fiscal_year), 0)             AS max_fy,
                      COUNT(DISTINCT org_name)               AS n_orgs,
                      COUNT(DISTINCT agency_ic_code)         AS n_ics
               FROM projects WHERE award_amount IS NOT NULL""",
            conn,
        )
    return df.iloc[0].to_dict()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true", help="don't write CSV/PNGs")
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    stats = summary_stats()
    print("Summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    save = not args.no_save
    print("\nFunding by agency × year:")
    print(funding_by_year(save=save).head(10).to_string(index=False))
    print("\nTop institutions:")
    print(top_institutions(save=save).head(10).to_string(index=False))
    print("\nState concentration:")
    print(state_concentration(save=save).head(10).to_string(index=False))

    if save:
        (RESULTS / "summary.json").write_text(json.dumps(stats, indent=2, default=str))
        print(f"\nResults written to {RESULTS}")


if __name__ == "__main__":
    main()
