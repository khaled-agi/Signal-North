# Worldwide country-lens discovery — Signal North

## What is extended

All 249 ISO 3166-1 countries/territories plus Kosovo (XK), a separately labeled
non-ISO research jurisdiction, receive a distinct news
discovery lens. Coverage levels are explicitly different:

1. Country indexed, but not yet scanned (no source coverage claimed).
2. A news scan attempted, with no relevant headlines accepted.
3. Unverified, dated and source-linked recent headline discoveries.
4. Official source-collected enforcement actions, from a SEPARATE workflow.
5. Failed or partial collection reported separately with dates.

Country is a search-market label, NOT verified publisher nationality, offender
location, victim location or confirmed incident coordinates. The map places
international reporting at a representative country centroid solely to browse
the monitoring market, not to locate any crime. Source counts are not
indicators of fraud prevalence.

## Local lens

- Every ISO market has an English country-named financial crime query.
- Selected markets add curated local-language fraud terms and native names,
  across Arabic, Spanish, Portuguese, French, German, Chinese, Japanese,
  Korean, Hindi, Swahili, Turkish, and other languages.
- Only explicitly configured markets use their own Google News edition;
  others are labeled English country-named fallback.
- Known official regulator homepages are published as editorial discovery
  directory links where configured. This does NOT imply regulator ingestion.
- Original published article titles, dates, publisher labels, source links,
  and evidence status are preserved. No article bodies are republished.

See scripts/world_country_lenses.py for edits to the curated source settings.

## Scheduled rotation and retention

The collector scripts/collect_world_news.py scans 16 rotating country lenses per
nominal 30-minute Github Actions job. A full pass is approximately eight hours
IF every scheduled job runs; actual timing varies. Up to two searches are used
per market: country-named English and a curated local-language term.

Only up to 21 days of recent discovered reporting are retained, maximum 18
records per market and 2,500 total. Snapshots and the rotating cursor are in:
- data/world_reporting.json
- data/world_reporting_status.json
- data/world_reporting_state.json

Use WORLD_NEWS_OFFLINE=1 for offline tests without claiming an actual scan.
WORLD_NEWS_BATCH is configurable from 1 to 32.

The official global enforcement pipeline and Canadian news and source-review
pipelines remain separate, and no new country-source metadata is automatically
presented as verified enforcement, bank losses or a researched incident.

## Limitations and ongoing expansion

This is NOT complete official enforcement ingestion for all 250 configured research jurisdictions.
Official national agency collectors must be built and verified individually.
Country-local reporting is only best-effort, and editions, syndication feeds,
language coverage and query relevance vary widely. Absence of articles or
enforcement records never establishes that fraud did not occur.

FATF's country information is available at
https://www.fatf-gafi.org/en/countries.html
and its AML regional network at
https://www.fatf-gafi.org/en/countries/global-network.html.
GDELT DOC 2.0 may provide complementary country-source news discovery in
a subsequent release, but source country is not crime location.

Tests:
  python -m unittest discover -s tests -p test_world_reporting.py
  python tests/smoke_site.py

## Non-ISO jurisdictions and transparent counts

The ISO 3166-1 list contains 249 countries and territories. Signal North also
includes Kosovo using the commonly used **XK** user-assigned identifier; XK is
not an official ISO 3166-1 alpha-2 code. Its research entry uses the Albanian
term *mashtrim* and links to the Central Bank of Kosovo's official homepage,
without treating that directory entry as an ingested enforcement source.

Other subnational, self-governing and disputed territories are not all separate
markets. For example, Ascension and Tristan da Cunha appear within ISO's
Saint Helena, Ascension and Tristan da Cunha (SH) entry. This catalogue should
not be described as every geopolitical entity or every separate legal/regulatory
jurisdiction, and inclusion does not imply diplomatic recognition.
