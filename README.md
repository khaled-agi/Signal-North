# Signal North — Canadian Financial Crime Intelligence

[Canada research](https://khaled-agi.github.io/Signal-North/) · [United States research](https://khaled-agi.github.io/Signal-North/us.html)

## United States nationwide workspace (October 2026)

Signal North now includes a separate, source-linked U.S. research interface for **all 50 states and Washington, D.C.**, at `/us.html`. The country switch is available on both research pages. National enforcement notices are **not** assigned to states from an institution's headquarters, litigation venue, or the agency's address.

- **Original federal enforcement:** `scripts/collect_us.py` reads publicly published **FinCEN** BSA/AML actions and **CFPB** consumer financial-law case listings. It preserves prior notices when source parsing fails. The initial snapshot is seeded with a small, directly sourced selection that distinguishes later dismissed, modified or terminated proceedings. **It is not an exhaustive catalog of U.S. federal, state, or local enforcement.**
- **State-wide news discovery:** Rotates Google News U.S. RSS searches through eight U.S. states or D.C. each scan, plus national queries. All 51 jurisdictions appear in the geography selector immediately. A marker is created only when a state is literally supported by the headline; it uses an approximate state-capital reference position and **does not claim to show where an incident occurred**.
- **Source types:** FinCEN/CFPB regulator-index records are official-source evidence of public enforcement listings, not necessarily final legal findings. Google News headlines are **unverified discovery leads**, not verified cases, fraud rates, or established losses.
- **Research workflows:** Explore a U.S. reporting map, filter by jurisdiction/evidence/date, review original source documents and procedural case statuses, compare source publication coverage over time, and investigate separately named organizations.
- **Other agencies:** The sources directory links to FTC Consumer Sentinel data, FBI IC3, DOJ, SEC, OCC, FDIC, FINRA, and all state attorneys general. Those appear as **reference only** unless a dedicated parser is introduced and validated. US coverage should not be marketed as complete until additional official and local sources are ingested.
- **Pipeline:** `.github/workflows/pages.yml` collects U.S. evidence and publishes `data/us_enforcement.json`, `data/us_news.json`, `data/us_status.json`, and `data/us_states.json`. `tests/test_us_logic.py` and `tests/smoke_us.py` enforce geographic, legal-status and rendered-UX safeguards.

## Canada community research network update

(October 2026)

Signal North now supports two audiences: financial-crime researchers investigating public evidence, and community members contributing **publicly sourced** stories and corrections. The old client watchlist is still available under specialized views for personal, browser-local research, but is no longer the platform's primary organizing concept.

The main workflow is **Discover → Study scam themes → Investigate institutions/sectors → Contribute evidence**.

- **Scam themes:** `scripts/build_theme_trends.py` derives a year-by-year multi-label article-headline taxonomy in `data/theme_trends.json`. Chart counts measure **discovered headline coverage, not fraud incidence**; articles may match multiple topics.
- **Sector intelligence:** `data/sector_watch.json` curates source-linked regulator decisions, crypto-platform authorization, institutional fraud warnings, casinos/lotteries, and AML administrative penalties. **Being authorized or impersonated is not wrongdoing.**
- **Community:** `.github/ISSUE_TEMPLATE/public-source.yml` and `correction.yml` accept public source suggestions and corrections for moderator review. Nothing from GitHub Issues auto-publishes. This is **not anonymous** and not a confidential crime-reporting channel. See `CONTRIBUTING.md`.
- **Historical discovery:** Rolling GitHub Actions searches rotate among 2020–2026 and expand to fintech, Wealthsimple, crypto, gambling, iGaming, identity theft, recovery scams and other typologies.
- **Social signals:** Public social-media links may be suggested as unverified source leads through the community form. There is **no unauthorized direct Reddit scraping or automatic social-media ingestion**. API approval, privacy review and platform terms are prerequisites.
- **True anonymous/private reporting:** Not yet offered. A static public site cannot safely store sensitive submissions. A separate server-side moderation, privacy, retention and abuse-prevention system is required before launch.



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

## Evidence connections and analyst workflow

The **Evidence connections** tab joins three distinct categories by explicit institution identity, using aliases such as RBC/Royal Bank of Canada and TD/Toronto-Dominion Bank.

**Regulatory enforcement:** FINTRAC and FCAC published decisions, penalties and dates; not fraud losses. FCAC "$4.25M" amounts are now parsed as millions.

**Source-reviewed reported cases:** Customer/police/media reports with explicit institution roles, source links, amounts distinguished as customer losses, credit exposures or recovered funds. Bank involvement never automatically establishes bank fault.

**Unverified headline leads:** Google News and historical archives, RCMP divisional Atom feeds and Canadian publisher RSS metadata. GDELT may return HTTP 429 and is not counted when rate-limited.

At each collection, Python regenerates source-linked institution_intelligence.json and review_queue.json. Canonical bank names use exact known aliases, not misleading substring matching. Investigative topics are keyword-based research signals, never findings of wrongdoing.

The analyst review queue supports local New / In review / Documented / Dismissed statuses, research notes and CSV export. Documented means the analyst has examined a story; it does not promote a headline to a verified case. Watchlist client stages and notes also remain browser-local, not team-synchronized.

The unified multi-year article repository retains original publisher URLs and metadata, not copyrighted article bodies. Grouping near-identical titles within a month reduces repeated syndicated links, but independently worded stories about one underlying fraud event may still remain separate. Article publication date differs from incident date where known.

## Deployment and quality assurance

GitHub Pages remains the canonical website, using the Replit editorial white styling. The refresh button reloads published source snapshots; it never directly triggers a scan. The GitHub Actions collector checks sources on a best-effort schedule.

The Python logic tests validate penalty scale and conservative evidence joins. The Chromium smoke suite checks article dates and pagination, map controls, source-reviewed cases, cross-source institution evidence, local client watchlist actions and source-review workflow. Source health is displayed in the website.

Automatic full-article parsing requires lawful access and stronger verification before any client-ready conclusions can be stated. Shared team watchlists and outbound notifications need authentication and a backend. No public data source can guarantee complete Canadian fraud-news coverage.
