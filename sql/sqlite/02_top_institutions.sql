-- Top recipient institutions by total award, with rank and share of total.
WITH per_org AS (
    SELECT
        org_name,
        COUNT(*)                              AS n_projects,
        SUM(award_amount) / 1e6               AS total_award_m
    FROM projects
    WHERE award_amount IS NOT NULL AND org_name IS NOT NULL
    GROUP BY org_name
),
totals AS (SELECT SUM(total_award_m) AS grand_total FROM per_org)
SELECT
    org_name,
    n_projects,
    ROUND(total_award_m, 2)                                                 AS total_award_millions,
    RANK() OVER (ORDER BY total_award_m DESC)                               AS rank,
    ROUND(100.0 * total_award_m / (SELECT grand_total FROM totals), 2)      AS share_pct
FROM per_org
ORDER BY total_award_m DESC
LIMIT 25;
