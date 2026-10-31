# First complaint-data integration: U.S. CFPB

This release integrates ONE new complaints data source:
**Consumer Financial Protection Bureau (CFPB) Consumer Complaint Database**.
CAFC, OBSI, FCAC complaints, UK FOS and AFCA are NOT yet implemented.

Official documentation:
- Public database: https://www.consumerfinance.gov/data-research/consumer-complaints/
- Search API: https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/
- Specification: https://cfpb.github.io/ccdb5-api/documentation/
- 2026 release notes: https://cfpb.github.io/api/ccdb/release-notes.html
- Field definitions: https://cfpb.github.io/api/ccdb/fields.html

## Collector behavior

The scheduled GitHub Actions run executes scripts/collect_cfpb_complaints.py.
It requests ONE page of up to 100 recently received published complaints,
bounded to the previous 90 days and sorted most recent-first. This is the
CFPB public search API, not the retired filtered JSON export. Successful
runs merge IDs into a rolling, deduplicated local sample capped at 2,500
records and a 90-day lookback.

Only categorical fields are saved:
- Complaint ID and received date
- Company, product/subproduct, issue/subissue
- Consumer state, company response category, response timeliness
- Original CFPB public record URL, source and evidence status

Excluded completely: narrative text, attachments, ZIP code, personally
identifying information, complaint descriptions, tags, raw API responses.
This integration uses no non-public CFPB government/enterprise systems.

## Critical coverage limitations

This is a bounded rolling recent sample, NOT a census of all complaints.
The search API has a documented 100-item maximum per request. Complaints
can arrive faster than new records are archived by the scheduled collector.
Breakdowns within the observed sample are not population totals, company
misconduct rates, company rankings, or representative market trends.

If the API reports an exact matched total for the query, it is stored in
source health for context only, never used to infer sampled company shares.
Some CFPB complaints are excluded from the public database altogether.

The latest published API release notes (Sept 2026) say consumer narratives
were removed and filtered JSON exports retired. This integration asks the
separate documented search API for JSON search results. If the endpoint
fails or changes, the collector records an error and preserves previously
collected records, rather than creating fake complaint records.

## Site and provenance

News & Reporting → U.S. consumer complaints · CFPB contains a collapsed
panel with company/issue search, product and state filters, and source links.
Its records are consumer allegations—not substantiated fraud, regulator
findings, control failures, or enforcement actions. Consumer state is a
mailing-address state, NOT an alleged fraud location. These data never create
fraud map markers or feed into the enforcement list.

No narratives or ZIP codes are displayed or collected. Source health shows
attempted/failed/not-scanned accurately.

Data outputs:
- data/cfpb_complaints.json
- data/cfpb_complaints_status.json

To test without a request: CFPB_OFFLINE=1 python scripts/collect_cfpb_complaints.py

Checks:
- python -m unittest discover -s tests -p test_cfpb_complaints.py
- node --check cfpb.js
- python tests/smoke_site.py

Browser tests inject a fixture in their own sandboxed HTTP response;
no synthetic complaint is included in the deployed JSON data.

## Banking-product discovery (October 30 expansion)

The original recent-only CFPB collector ran successfully on October 31 UTC
and populated 100 genuine records. That first page was dominated by credit
reporting and debt collection (95 of 100), with only two checking/savings
complaints. Therefore, using the newest 100 general complaints alone would
mislead bank-focused users.

The next collection release uses documented CFPB product filters and makes
FOUR bounded API requests per run: one all-products recent page, plus three
rotated banking-product pages. The configured sectors are checking/savings,
credit card, money transfer/virtual currency, mortgage, and vehicle loans.
Each request is limited to 100; query success, filters, error states and
returned page counts are tracked separately. The rotation cursor persists in
data/cfpb_complaints_state.json. Category windows are not complete censuses.

The browser adds a company-name dropdown using names actually returned by
CFPB. Exact company names are retained: no guessed parent-company grouping
or inference that every named company is a chartered bank. Complaints are
still allegations, not confirmed misconduct. Comparing raw complaint counts
across institutions with different customer counts or business models is
inappropriate. Newly published records appear only after a successful live
CFPB scan; CI tests use fictitious fixture data exclusively inside tests.
