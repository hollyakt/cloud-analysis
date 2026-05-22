-- State-level concentration of NIH funding (US only): total $, share, and
-- Herfindahl-Hirschman-like concentration of institutions within each state.
WITH us_only AS (
    SELECT * FROM projects
    WHERE award_amount IS NOT NULL
      AND org_country = 'UNITED STATES'
      AND org_state IS NOT NULL
),
per_org_state AS (
    SELECT
        org_state,
        org_name,
        SUM(award_amount) AS org_award
    FROM us_only
    GROUP BY org_state, org_name
),
state_totals AS (
    SELECT
        org_state,
        SUM(org_award)                                  AS state_award,
        COUNT(*)                                        AS n_orgs
    FROM per_org_state
    GROUP BY org_state
),
shares AS (
    SELECT
        pos.org_state,
        org_name,
        org_award * 1.0 / state_award AS org_share
    FROM per_org_state pos
    JOIN state_totals st USING (org_state)
)
SELECT
    st.org_state,
    st.n_orgs,
    ROUND(st.state_award / 1e6, 2)                                     AS state_total_millions,
    ROUND(SUM(s.org_share * s.org_share), 4)                           AS hhi,
    -- HHI ~ 1 means one institution dominates; ~ 1/n_orgs means even spread.
    ROUND(100.0 * MAX(s.org_share), 1)                                 AS top_org_pct
FROM state_totals st
JOIN shares s USING (org_state)
GROUP BY st.org_state, st.n_orgs, st.state_award
ORDER BY state_total_millions DESC;
