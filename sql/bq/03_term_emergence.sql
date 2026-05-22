-- BigQuery-specific: split the API's "<term1><term2>..." blob into rows
-- with SPLIT + UNNEST, then compare recent vs prior-year term frequency.
-- This query relies on UNNEST(SPLIT(...)) which has no clean SQLite parallel.
WITH terms_long AS (
    SELECT
        project_num,
        fiscal_year,
        TRIM(t, '<>') AS term
    FROM `{project}.{dataset}.projects`,
    UNNEST(SPLIT(REPLACE(terms, '><', '>|<'), '|')) AS t
    WHERE terms IS NOT NULL AND TRIM(t, '<>') != ''
),
year_buckets AS (
    SELECT
        term,
        SUM(CASE WHEN fiscal_year >= 2022 THEN 1 ELSE 0 END) AS recent_count,
        SUM(CASE WHEN fiscal_year <  2022 THEN 1 ELSE 0 END) AS prior_count
    FROM terms_long
    GROUP BY term
    HAVING COUNT(*) >= 10
)
SELECT
    term,
    recent_count,
    prior_count,
    recent_count - prior_count AS delta
FROM year_buckets
ORDER BY delta DESC
LIMIT 30;
