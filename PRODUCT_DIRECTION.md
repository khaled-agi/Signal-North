# Signal North — Product Direction (October 2026)

## The product promise

**Find the evidence. Understand the exposure. Decide the next investigation.**

Signal North is a Canadian financial-crime research workspace for bank fraud investigators, financial crime consultants, and intelligence teams. It is NOT an automated score of bank wrongdoing or a list of consulting leads inferred solely from negative coverage.

## One workflow, five navigational destinations

1. **Command center** — What changed? Concise fresh developments, national map, four unambiguous counts. Additional panels collapse by default.
2. **Discover stories** — What are journalists and police reporting? The multi-year, multi-source archive with year/month/typology/bank filters and geocoded headline references.
3. **Investigate institutions** — Who is actually linked to this evidence? Canonical institution identity and source-separated timeline: regulatory actions, source-reviewed reported incidents and unverified headline mentions.
4. **Client workspace** — What should I do next? Local watchlist, analyst stages, research notes, case triage and sourced brief export. An authenticated shared workspace is required before team CRM use.
5. **Research library** — What is the wider threat? Official CAFC, OBSI, FCAC, CSA and Statistics Canada research, with date ranges and caveats, plus source-linked historical national loss comparisons.

Specialized views (reported cases, regulator records, penalty figures, institution directory, source health) remain accessible under an expandable secondary menu, instead of competing as equal homepage priorities.

## The model: connect objects, not merely URLs

A reliable product requires distinct objects:

- **Source:** Original publisher/government document and URL, publisher, publication date, capture date, and source type.
- **Article:** One piece of reporting (not necessarily one incident). Keep all supporting URLs, detect duplicates, retain original title.
- **Incident:** One underlying reported fraud event with reported incident period, scam typology, financial impact type, geography role and bank involvement role. No automatic promotion from headline to confirmed incident.
- **Regulatory action:** Publication and underlying proceeding dates, legal status, institution, penalty, amount/currency and regulator. Not a customer loss.
- **Institution:** Verified legal entity plus reviewed aliases, group/parent only where explicitly documented. Roles such as "account provider", "impersonated brand", "enforcement subject" and "bank not named" must not be conflated.
- **Research signal:** Investigator hypothesis supported by specific records, plus counterevidence and unanswered questions. Never a guilt prediction.
- **Client work item:** Analyst owner, status, notes, next action, verified evidence and review date. Authentication and permissions required for production team use.

Data flow:

```
Original publications and open datasets
               ↓
Metadata discovery and source registration
               ↓
Article deduplication / provenance / historical indexing
               ↓
Human-verified incident review and explicit institution role
               ↓
Source-separated institution timeline / geographic context
               ↓
Analyst hypothesis, follow-up and client research brief
```

## Acquisition and historical coverage

Google News RSS runs frequently but is incomplete; yearly backfills seek older publications by monthly date windows. Publisher feeds and RCMP releases add independent leads where reliable. GDELT often returns 429 from shared CI runners; treat it as unavailable unless a successful accepted-source count is logged. Keep source-health diagnostics and date of last complete run.

The years 2020–2023 are being added via a dedicated backfill job. Count only records actually retrieved and validated by source publication dates. A year with sparse feeds is **not** evidence of low fraud prevalence.

The official research library supplements newspaper discovery. A CAFC reported victim loss amount does not mean a bank-owned loss, and different historical source releases may revise the same year's loss total.

## Recommended next architecture, in priority order

**P1 — Persistent case-level evidence model.** Create incident_candidates with exact cited excerpt/URL and original publication date, dedupe across differing headlines using subject, amount, date, location and overlap, and require analyst review before publishing the canonical incident. Reversals/appeals/corrections must flow through existing records.

**P2 — Production-grade acquisition.** Add vetted provincial police and local media sources, automated schema validation, job timeouts/backoff, feed freshness indicators, source attribution and archived URL checks. Respect terms and copyrights; don't republish full articles without rights.

**P3 — Institution intelligence briefs.** Summarize recurring *documented* findings, separate sector trends from institution-specific facts, and include missing data and contradictory reports. Include reviewer name/date if used for client work.

**P4 — Team workflow.** Authenticated access, shared client research queues, action owners, source-linked case notes and controlled alert delivery. Browser localStorage is a prototype only.

**P5 — Evaluation.** Measure source diversity, time coverage, duplicate rate, geographic attribution precision, bank role precision, percentage of analyst-approved incidents, broken links and stale sources. More headlines alone is not the KPI.

## Guardrails

No invented bank-level fraud losses. No geographic pin from a bank headquarters merely because its name appears in a scam headline. Never equate money laundered, customer financial loss, regulatory penalty, unauthorized exposure and recovered funds. Keep alleged, investigated, charged, settled, imposed, paid and appealed separate.

Research should answer: **What does the primary evidence establish, what remains uncertain, and what should an analyst investigate next?**
