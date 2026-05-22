-- BigQuery dialect. Uses a cross-join with a one-row totals CTE for share %.
WITH per_org AS (
    SELECT
        org_name,
        COUNT(*)                              AS n_projects,
        SUM(award_amount) / 1e6               AS total_award_m
    FROM `{project}.{dataset}.projects`
    WHERE award_amount IS NOT NULL AND org_name IS NOT NULL
    GROUP BY org_name
),
totals AS (SELECT SUM(total_award_m) AS grand_total FROM per_org)
SELECT
    org_name,
    n_projects,
    ROUND(total_award_m, 2)                                                 AS total_award_millions,
    RANK() OVER (ORDER BY total_award_m DESC)                               AS rank,
    ROUND(100.0 * total_award_m / totals.grand_total, 2)                    AS share_pct
FROM per_org, totals
ORDER BY total_award_m DESC
LIMIT 25;
