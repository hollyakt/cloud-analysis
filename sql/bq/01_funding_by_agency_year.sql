-- BigQuery dialect. Replace {project}.{dataset} with your destination.
-- Same analytical intent as sql/sqlite/01_funding_by_agency_year.sql.
SELECT
    fiscal_year,
    agency_ic_code,
    ANY_VALUE(agency_ic_name)                                                  AS agency_ic_name,
    COUNT(*)                                                                   AS n_projects,
    ROUND(SUM(award_amount) / 1e6, 2)                                          AS total_award_millions,
    ROUND(SUM(SUM(award_amount) / 1e6) OVER (
        PARTITION BY agency_ic_code ORDER BY fiscal_year
    ), 2)                                                                      AS cumulative_millions
FROM `{project}.{dataset}.projects`
WHERE award_amount IS NOT NULL AND fiscal_year IS NOT NULL
GROUP BY fiscal_year, agency_ic_code
ORDER BY fiscal_year, total_award_millions DESC;
