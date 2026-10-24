# Signal North

Canada-focused, source-linked financial crime and regulatory enforcement intelligence.

This repository powers a public, read-only map and event tracker for regulatory decisions. All automated claims must link to original primary sources. It is **not** a fraud ranking of banks and does not infer wrongdoing from a customer complaint or an allegation.

## Architecture

- `scripts/collect.py` retrieves and parses Canadian regulatory sources into dated event records.
- `data/events.json` stores cumulative, deduplicated regulator-sourced events.
- `index.html` is a GitHub Pages dashboard with a map, search, filters, institution profiles, and source links.
- `.github/workflows/pages.yml` runs collection daily and publishes the site.

## Deploy

In **Settings → Pages**, set Build and deployment **Source: GitHub Actions**. Check Actions for the initial `Update intelligence and deploy` run. GitHub Pages publishes at `https://khaled-agi.github.io/Signal-North/` after the first successful run.

## Coverage and limitations

This is an evolving research prototype, not a comprehensive registry of financial crime. FINTRAC and FCAC provide public enforcement records; CIRO proceedings may be preliminary and must not be represented as confirmed findings. No unverified media allegations are auto-published. Notices can be updated, appealed, or removed, so original source URLs and legal status matter.

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/collect.py
python -m http.server 8000
```

Open http://localhost:8000. Collector network access is required to retrieve new records.
