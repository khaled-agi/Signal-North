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

The collector scripts/collect_world_news.py scans 32 rotating country lenses per
nominal 30-minute GitHub Actions job. All 250 markets are covered in its
rotation, but not all will have completed a scan at any given time. At the
nominal schedule, a full rotation takes approximately four hours, subject to
actual Actions execution and source failures. Three English thematic queries
run for every market. Where configured, an additional native-language query
runs with a national or same-language edition (when supported), or an
explicitly labeled fallback.

Up to 120 days of previously discovered reporting are retained (not 120 days
of historical backfill), maximum 90 geographically referenced reports per
market and 12,000 total. The separate, strictly **unlocated** local-language
candidate feed holds up to 25 per search market and 3,500 total. Its records
must never be used as country-enforcement or incident-map data.
Snapshots and the rotating cursor are in:
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

## Geographic reference completeness

Of the 250 configured ISO and non-ISO research markets, 248 have an
approximate browsing coordinate. Antarctica (AQ) and the geographically
scattered United States Minor Outlying Islands (UM) do not have a meaningful
single representative point and intentionally remain unplotted when news is
indexed. This is not a collection omission and never changes the country
filter. No browsing coordinate is a verified incident address.

## 2026 worldwide content ingestion expansion

The website distinguishes **three** core evidence classes plus a separate
unattributed native-language discovery queue. The country-lens expansion
configures 157 LOCAL search profiles in addition to 250 English baselines;
some profiles have English as their local language and therefore avoid
redundant extra English queries. Original headline language is not inferred
from the language of the search query.

The website distinguishes **three** source classes:

- **Unverified news headlines:** country-aware Google News RSS searches for all
  250 ISO/non-ISO research markets, two financial-crime theme queries plus a
  local-language query where configured. Each scheduled scan covers up to
  32 markets, cycling through the catalogue over about four hours if jobs run
  at their nominal half-hour frequency. Up to 120 days of accepted metadata
  are retained after discovery (up to 90 per country and 12,000 overall).
  This is not an exhaustive archive of everything published in that period.
- **Official enforcement-index entries:** actual regulator index listings
  collected directly from named authorities. Current primary-source index
  collectors are FinCEN (US), FCA (UK) and MAS (Singapore); separately
  source-reviewed historic entries remain preserved. Being listed does NOT
  automatically imply criminal guilt or that a decision is final.
- **Original-regulator-domain publication leads:** GDELT identifies candidate
  news announcements originating on 30 specified official agency domains.
  Every URL is checked against the EXACT government/agency domain, and every
  title must mention an enforcement-related action. Index first-seen dates
  are explicitly NOT official publication or decision dates. These records
  are separate from verified index entries, and contain no inferred penalties
  or institutional blame. About six agencies are scanned in each scheduled run.
  Some agencies will not return results, and their status is visible.

The complete world enforcement pipeline would require individually validated
country-level regulators, local-language legal-status parsers, archived orders,
appeals, settlement overlap, date-normalization and source freshness.
30 source-domain search targets **do not** mean enforcement is covered for all
250 countries. Neither GDELT nor syndicated news provides complete country
or official enforcement coverage. A country with zero collected actions must
never be labeled a jurisdiction with zero enforcement.

Data files:
- data/world_reporting.json and data/world_reporting_status.json
- data/global_enforcement.json and data/global_source_status.json
- data/global_regulator_publications.json and
  data/global_regulator_publications_status.json
- data/world_jurisdictions.json (actual counts for each evidence tier)

The worldwide news browser under News & Reporting supports search, typology,
country selection, load more and all matches. The Enforcement tab has a
**separate** original-regulator-domain publication browser with country,
agency and text filters. The map keeps the three evidence categories distinct.


## Local-language coverage expansion and geography integrity

**New native-language terms:** the curated research vocabulary now includes
additional markets in North and West Africa, Eastern and Northern Europe, Latin
America, Central Asia, the Caucasus, the Pacific and Southeast Asia. A profile
means a search is configured; it does not guarantee an edition exists, that
the returned publisher is domestic, or that every story is relevant.

**Edition selection:** the three English queries use an English-language Google
News edition. Local-script queries use a same-language country edition where
known, a *labeled language-proxy edition* where available, or an English edition
fallback with native keywords. The site preserves the headline as received.
The field `query_language` identifies the SEARCH language, not independently
detected source language. The `query_edition_basis` field records how the
edition was selected.

**Two distinct original-language outputs:**
1. If the article headline explicitly names the country or a curated local name,
   it may be included in country-referenced news. Even then it is **not a
   verified incident location**, and no offence is inferred.
2. If a native-language query finds a fraud headline that does not name its
   target country, the article is instead stored in
   `data/world_local_unattributed.json`. It is accessible in a collapsed
   source-research list, labeled with the search market only. It gets **no
   map marker, no attributed country, and no place in official enforcement**.

English and local-language versions of the same reporting may both appear.
Full cross-language event merging is intentionally deferred.


## African and Asian market-depth expansion

An ISO country entry is not evidence of local coverage. The country-wide
rotation continues to scan all 250 configured research markets. In addition,
`scripts/region_query_lenses.py` defines language- and sector-specific search
phrases for major markets across:

- Mainland China: simplified-Chinese cyberfraud and money-laundering queries;
  Hong Kong/Taiwan retain distinct edition and jurisdiction labels.
- India: existing English/Hindi plus Tamil, Bengali, Telugu and Marathi
  fraud reporting. Google News unsupported local editions use an explicitly
  tagged English India edition fallback; they are not reported as native
  publisher editions.
- Malaysia: Malay online fraud, simplified-Chinese fraud, Tamil fraud;
  Chinese edition searches are proxies and do NOT establish Malaysian source
  nationality or incident geography.
- Other Southeast Asian markets: Indonesia, Thailand, Vietnam, Philippines,
  Singapore, Cambodia, Laos, Myanmar, Brunei and Timor-Leste.
- African countries: Nigeria, Kenya, Tanzania, Uganda, South Africa, Ghana,
  Ethiopia, Egypt, Morocco, Algeria, Tunisia, Senegal, Côte d'Ivoire,
  Cameroon, DR Congo, Rwanda, Angola, Mozambique, Zambia and Zimbabwe.

All other countries retain the English baseline and configured local
languages. Queries are capped per market: they are not an exhaustive crawl.
Some source editions or languages will return zero matches. Original-language
results with no supported country mention remain in the separate unmapped
`data/world_local_unattributed.json` queue.

A second deterministic priority rotation scans up to four additional hub
markets per scheduled run, alongside (never instead of) the existing 32-market
worldwide baseline. It covers China, India, Malaysia, Indonesia, Thailand,
Vietnam, Philippines, Singapore, Cambodia, Nigeria, Kenya, South Africa,
Egypt, Ghana, Tanzania and Ethiopia.

The frontend News & Reporting browser now offers Africa, Southeast Asia,
South Asia and East Asia regional filters for *country-referenced* headlines
and separately labeled unlocated discovery candidates.

**Country evidence and non-spaced scripts:** Chinese and certain South/Southeast
Asian writing systems do not necessarily place whitespace around a country
name. Both the collector and map checker explicitly support native-script
country mentions, including Chinese 中国, Malay-targeted Mandarin 马来西亚,
and Tamil இந்தியா. A country *mention* does not prove an event took place
there. RSS edition, journalist language, publisher domicile, victim location,
and regulator jurisdiction remain distinct concepts.

The actual number of successful searches and accepted article leads is
reported by the latest source-status snapshots, not predicted from the
configured country or query count. Cross-language event deduplication is
intentionally deferred.
