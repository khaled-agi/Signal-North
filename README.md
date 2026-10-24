# Signal North — Canadian Financial Crime Intelligence

[Open the live dashboard](https://khaled-agi.github.io/Signal-North/)

Source-linked research tool for Canadian regulatory enforcement, individual victim fraud cases, fraud trends and Google News discovery.

## What's available

| Dataset | Files | Refresh | Evidence standard |
|---|---|---|---|
| Enforcement notices | `scripts/collect.py`, `data/events.json` | Hourly | Primary regulator notices (FINTRAC, FCAC) |
| Fraud news leads | `scripts/collect_news.py`, `data/news.json` | Hourly | Syndicated titles for discovery **only**, not validated cases |
| Source-reviewed customer incident reports | `data/incidents.json` | Curated from source-checked police releases / reputable media | Source-attributed customer-loss, credit exposure and recovery cases, **never** inferred bank culpability |
| National fraud losses | `data/fraud_stats.json` | Curated on source publication | CAFC/OBSI original published figures |
| Bank-owned fraud losses | `data/bank_disclosures.json` | Only as independently disclosed | Empty until an attributable, verified bank-year disclosure exists |

The website shows:
- Layered Canada map with grouped institution enforcement notices, source-reviewed customer incidents, and **unverified** Google News city mentions. Filter by province and major penalty amount.
- Source-reviewed reported fraud incident explorer, with bank role, scam type, customer impact, incident period, source and location.
- Current Google News scam and bank fraud headlines shown directly on the dashboard with last-scan timestamp; headline-only bank and amount extraction.
- Enforcement explorer and institution profiles
- Fraud intelligence: reported losses by fraud type and year, plus syndicated headline leads
- Annual enforcement penalties by institution, with banks/credit unions filter
- Source catalog and research limitations

## Important financial distinctions

1. **Reported victim fraud losses**: amounts reported to CAFC by the public, nationwide or by typology. Not losses borne by banks.
2. **Bank-owned fraud losses**: an actual bank's measured losses due to fraud, only reportable with a source naming its legal entity, financial period, currency and measurement basis. Publicly unavailable amounts stay undisclosed.
3. **Regulatory penalties**: fines imposed for AML, consumer protection and related deficiencies. They are costs/penalties, **not fraud losses**.
4. **Proceeds of money laundering**: amounts moved through an account or network; not synonymous with bank losses.

A name appearing in a syndicated headline does not prove the bank committed any offence or incurred a loss. News leads are **not** included in official enforcement statistics or automatic institution scoring.

## Map and geographic methods

Uses OpenStreetMap tile imagery with attribution. The map pins represent explicitly supported locations of institutions reported in regulator notices, never an automatically assumed location of a crime. Unlocated incidents remain searchable but are not pinned. Nationwide CAFC totals are not distributed to individual provinces or banks. Broad release of the site should use a commercially suitable map-tile provider as traffic grows.

## Sources and next priorities

**Running:** [FINTRAC](https://fintrac-canafe.canada.ca/pen/4-eng), [FCAC](https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html), Google News RSS discovery (English and French, filtered, unverified).

**Curated:** [CAFC 2025 statistics](https://centreantifraude-antifraudcentre.ca/features-vedette/2026/02/top-fraud-2025-fraudes-plus-courantes-eng.htm), [CAFC H1 2026 bulletin](https://centreantifraude-antifraudcentre.ca/features-vedette/2026/08/fraud-trends-tendances-matiere-fraude-eng.htm), [OBSI 2025](https://www.obsi.ca/en/news/posts/obsi-2025-annual-report-released/).

**Next primary sources:** [CAFC open reporting dataset](https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f) (anonymized, currently through Q3 2025), RCMP/local police incidents, CIRO, CSA/OSC/AMF warning lists, OBSI complaint data, OSFI legal-entity registry, Canadian bank annual disclosures, and incident disclosures by the Privacy Commissioner.

## Deploy and update

Pages must be set to **GitHub Actions** under Settings → Pages. The `.github/workflows/pages.yml` workflow runs on the :07 and :37 minute marks (best effort) and on code pushes; GitHub scheduling is best-effort, not a guaranteed real-time interval. The dashboard is a GitHub Pages **static site**; its Refresh button fetches the latest published data snapshot and cannot scrape sources on demand.

The automated browser checks run in GitHub Actions and validate rendered records and filters.

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/collect.py
python scripts/collect_news.py
python -m http.server 8000
```

Open http://localhost:8000.

## Publication safeguards

Syndicated headlines must be reviewed against original publications before extracting fine amounts, victim counts or institutional involvement. Sources and publications can change or be appealed. Provenance and outcomes matter more than record volume. Nothing in this dataset should be used as a bank wrongdoing ranking or as proof that an organization is shopping for consultants.

## New case intake workflow

1. Google News RSS discovers stories and recent research (scheduled roughly every 30 minutes; not a true streaming feed).
2. Headline-only parsing records candidate bank names, quoted amount text, and city mentions; **these are unverified hints**.
3. Source-reviewed case entries go into `data/incidents.json`, with separate story publication and incident period, a precise role for each bank, and an amount category (victim loss, unauthorized exposure, or recovered funds).
4. Only source-supported case locations appear as blue markers. Orange markers are headline-city mentions and do not prove the incident occurred there.
5. Confirmed regulatory actions remain in their own layer, and penalties of C$1 million or more appear in the Major Enforcement panel. These are not necessarily consent orders.

A public GitHub Pages site cannot directly initiate authenticated workflow dispatch without exposing credentials. Use **Run source scan** to visit the GitHub Actions workflow and select **Run workflow** after signing in; **Refresh snapshot** reloads already published records.
