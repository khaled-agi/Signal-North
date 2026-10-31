# Canadian Anti-Fraud Centre (CAFC) open reporting data

Source: **Royal Canadian Mounted Police (RCMP) / CAFC**, officially published
on Canada's Open Government portal:

https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f

The published CSV covers **January 1, 2021 through September 30, 2025**
(as extracted October 1, 2025, approximately 75.5 MB). The official
dataset notes a delayed Q4 2025 update due to an intake system change.
No current-to-2026 coverage is claimed from this file.

## Data fields and limits

The CAFC dictionary documents Date Received, Country, Province/State,
Fraud and Cybercrime Thematic Categories, Solicitation Method,
Number of Victims and Dollar Loss, as well as demographic fields and
individual report identifiers. The connector intentionally **does not
publish or retain** individual report IDs, gender, victim age, free text,
or any individual-level information.

Only Canada-labelled public rows are included in the aggregations:
- by received year
- by fraud and cybercrime thematic category and received year
- by reporter province/state and received year
- by solicitation method and received year
- by province, fraud category and received year (suppressed below 5 rows)

Cells containing fewer than five report rows are suppressed.
The underlying raw CSV is processed into a temporary file on the
GitHub runner; it is never published to GitHub Pages.

The reported loss field may be blank; missing data are **not** converted
into zero. The output records missing amounts and never treats an
incomplete aggregate as a known full reported loss.
Likewise, report rows, unique victims, money losses and offences are
different measures. Any figure is an allegation supplied through the
CAFC reporting system, not a judicial finding or audited loss.

## Collection and source health

Collector: scripts/collect_cafc_open_data.py

Data: data/cafc_aggregates.json and data/cafc_source_status.json

The CSV is checked at most once per seven days after a successful run;
this reduces needless repeated 75 MB downloads. Source failures record
the error type without overwriting previously collected good data.
GitHub Actions runs are marked optional, and a failed download cannot
be mistaken for an empty report count.

No live collection is claimed before a successful production run.

Site: News & Reporting > Canadian fraud reports · CAFC

CFPB and CAFC cannot be combined into one raw complaint total:
- CFPB concerns U.S. consumer financial products reported to named companies.
- CAFC concerns Canadian and other fraud and identity-crime reports;
  this integration aggregates Canada-labelled rows only.
- Neither is an independently confirmed collection of criminal cases,
  nor should a reporter province be treated as an offence location.

## Validation

python -m unittest discover -s tests -p test_cafc_open_data.py
node --check cafc.js
python tests/smoke_site.py

CI supplies small synthetic data *only inside tests*. Public data JSON
starts empty and becomes populated only from official source downloads.
