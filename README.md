# Cloud-Connected Research Funding Analysis

Pulls federal biomedical research grants from the **NIH RePORTER** API into a local SQLite snapshot, then runs the same analytical workload two ways:

1. **Locally**, against SQLite — out of the box, no credentials required.
2. **On Google BigQuery**, against a dataset loaded from the same snapshot — for the cloud-native path.

The two paths produce the same numbers. The repo includes the cached outputs of a real run (`results/`) so a reviewer can verify end-to-end behaviour without setting up GCP.

## Why this shape

A real cloud project usually looks like this: data lands somewhere local or in cheap blob storage, the heavy analytical SQL runs in the warehouse, and a thin Python layer orchestrates and visualizes. The two SQL flavours under [sql/sqlite/](sql/sqlite/) and [sql/bq/](sql/bq/) are intentionally near-identical so the BigQuery path can be reviewed against the SQLite path without running it.

## Architecture

```
  NIH RePORTER REST API (api.reporter.nih.gov, no auth)
                 │
                 ▼
       ┌────────────────────┐
       │  src/fetch.py      │   paged JSON, flatten nested fields
       └─────────┬──────────┘
                 ▼
        ┌─────────────────┐
        │  SQLite snapshot │   data/reporter.db
        └────┬───────┬────┘
             │       │
   src/analyze.py    │              ── local path
             │       │
             ▼       ▼
   results/*.csv,*.png
                     │
                     ▼ src/bq.py load
            ┌───────────────────┐
            │  BigQuery dataset │   {project}.reporter.projects
            └────────┬──────────┘
                     │
            src/bq.py query
                     │
                     ▼
            BQ-flavored SQL    ── cloud path
            (sql/bq/*.sql)
```

## Quickstart — local path (no GCP required)

```bash
pip install -r requirements.txt   # core deps; cloud deps are extra

python src/fetch.py --years 2020 2021 2022 2023 --max-records 2000
python src/analyze.py
```

That produces:

```
results/
├── summary.json
├── funding_by_agency_year.csv
├── funding_by_agency_year.png
├── top_institutions.csv
├── top_institutions.png
└── state_concentration.csv
```

A snapshot of the same outputs from a real run is committed to the repo so you can inspect them without re-fetching.

## Quickstart — BigQuery path

```bash
pip install -r requirements.txt
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Load the local snapshot into BigQuery (WRITE_TRUNCATE, idempotent).
python src/bq.py load --project YOUR_PROJECT_ID --dataset reporter

# Run any of the BQ-flavored queries.
python src/bq.py query --project YOUR_PROJECT_ID --dataset reporter \
                      --sql sql/bq/01_funding_by_agency_year.sql --csv out.csv
python src/bq.py query --project YOUR_PROJECT_ID --dataset reporter \
                      --sql sql/bq/03_term_emergence.sql
```

The BQ SQL templates use `{project}` and `{dataset}` placeholders that `src/bq.py` fills at query time, so the same file works against any GCP project.

`03_term_emergence.sql` is BigQuery-only — it relies on `SPLIT` + `UNNEST` to unpack the API's `<term1><term2>` blob into a long table, which has no clean SQLite equivalent.

## Schema (`projects` table)

| Column                | Type     | Notes                                          |
| --------------------- | -------- | ---------------------------------------------- |
| `project_num`         | TEXT PK  | NIH project identifier                          |
| `fiscal_year`         | INTEGER  | Award FY                                        |
| `title`               | TEXT     | Project title                                   |
| `award_amount`        | REAL     | USD                                             |
| `org_name`            | TEXT     | Recipient institution                           |
| `org_state`           | TEXT     | 2-letter US state (NULL for non-US)             |
| `org_country`         | TEXT     | Country                                         |
| `agency_ic_code`      | TEXT     | NIH IC code (CA = NCI, NS = NINDS, …)            |
| `agency_ic_name`      | TEXT     | Full IC name                                    |
| `pi_first`, `pi_last` | TEXT     | Contact PI                                      |
| `terms`               | TEXT     | `<term1><term2>...` raw blob from the API       |

DDL: [src/db.py](src/db.py).

## Sample findings

From the cached run (2,000 NIH projects, FY 2020–2023):

**Top NIH ICs by funding** — National Cancer Institute, NIAID, and NHLBI dominate, consistent with NIH funding distribution overall.

**Top recipient institutions**:

| institution                          | n_projects | total ($M) |
| ------------------------------------ | ---------- | ---------- |
| Columbia University Health Sciences  | 105        | 52.3       |
| University of Wisconsin–Madison      | 9          | 31.4       |
| UC San Francisco                     | 52         | 24.7       |
| University of Chicago                | 27         | 19.6       |
| Duke University                      | 44         | 18.1       |

**State concentration (HHI)**. HHI near 1 means a single institution dominates the state's funding; near 1/N means an even spread:

| state | n_orgs | total ($M) | HHI    | top org % |
| ----- | ------ | ---------- | ------ | --------- |
| CA    | 24     | 117.0      | 0.114  | 21.1      |
| NY    | 17     | 94.1       | 0.330  | 55.7      |
| MA    | 19     | 86.9       | 0.356  | 56.3      |
| WI    | 4      | 33.4       | 0.882  | 93.8      |

California is diversified across many universities; Wisconsin is essentially one (UW-Madison).

Full results: [results/](results/).

## Design notes

- **Why NIH RePORTER.** The API is free, requires no auth, and the data (federal biomedical research grants) is directly in the science-of-science problem space (relevant for CSET-style analysis).
- **Two SQL dialects, one analytical contract.** [sql/sqlite/](sql/sqlite/) and [sql/bq/](sql/bq/) hold parallel queries. The two diverge only on dialect-specific features (`ANY_VALUE`, `UNNEST`, etc.). Comparing the two files is the simplest possible audit of the cloud path.
- **`WRITE_TRUNCATE` over `WRITE_APPEND`.** The BQ load is idempotent — re-running it overwrites the destination table. The local snapshot is the source of truth.
- **Credentials never committed.** `.gitignore` excludes `service-account*.json` and anything matching `gcp-credentials*.json`.

## Repo layout

```
cloud-analysis/
├── src/
│   ├── fetch.py       # NIH RePORTER → SQLite
│   ├── db.py
│   ├── analyze.py     # local analysis using sql/sqlite/
│   └── bq.py          # load + query against BigQuery
├── sql/
│   ├── sqlite/        # local-path queries
│   └── bq/            # BigQuery-flavored versions
├── results/           # cached outputs from a real fetch
├── data/              # SQLite DB (gitignored)
└── requirements.txt
```
