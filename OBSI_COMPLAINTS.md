# OBSI Canadian bank-level complaints — phase 1
Official source: https://www.obsi.ca/en/case-data-insights/data-cube/cases-by-banking-services-firms/

This integration creates a dedicated, clearly labeled source-navigation section under News & Reporting. It **does not yet ingest** bank-by-bank complaint totals into Signal North, because the OBSI data is distributed in an interactive Power BI Data Cube and an openly documented, stable bulk API/export has not been verified.

Official sources:
- Named banking firms and aggregate case outcomes: https://www.obsi.ca/en/case-data-insights/data-cube/cases-by-banking-services-firms/
- Product and issue breakdowns: https://www.obsi.ca/en/case-data-insights/data-cube/banking-products-and-issues/
- Named-bank, anonymized case summaries for federally regulated banks closed since June 30, 2022: https://www.obsi.ca/en/case-data-insights/banking-case-summaries/

## Next step for actual data ingestion
Validate a permitted export/data access method, then ingest firm/year/metric with source page, fiscal year, snapshot date, provenance and reporting scope. Prefer an official CSV export or authorization for programmatic access. For case summaries preserve bank, publication/close date, product, issue, outcome, public URL and redact any individual personal details. Unit-test firm disambiguation, missing metrics, annual fiscal boundaries and change in bank participation (single external complaints body from November 2024).

Never invent numeric complaint counts; never equate complaint volumes with misconduct. Keep OBSI escalated cases independent of CAFC fraud reports and U.S. CFPB complaints.
