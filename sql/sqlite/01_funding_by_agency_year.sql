-- Total NIH funding by Institute/Center (IC) and fiscal year, with running total.
SELECT
    fiscal_year,
    agency_ic_code,
    MAX(agency_ic_name)                                                       AS agency_ic_name,
    COUNT(*)                                                                  AS n_projects,
    ROUND(SUM(award_amount) / 1e6, 2)                                         AS total_award_millions,
    ROUND(SUM(SUM(award_amount) / 1e6) OVER (
        PARTITION BY agency_ic_code ORDER BY fiscal_year
    ), 2)                                                                     AS cumulative_millions
FROM projects
WHERE award_amount IS NOT NULL AND fiscal_year IS NOT NULL
GROUP BY fiscal_year, agency_ic_code
ORDER BY fiscal_year, total_award_millions DESC;
