# Signal North — Product & Design Brief

## Primary user
Canadian financial-crime consultants and fraud analysts who monitor target financial institutions and emerging threats.

## Information architecture
1. **Intelligence overview:** date-stamped snapshot, newest article discoveries, mapped events, headline links, big penalties, recently reviewed incidents.
2. **Fraud intelligence:** combined Google News recent and historical archive with year, month, typology, bank-name-in-headline filters and progressive pagination.
3. **Map:** verified regulator notices, reviewed victim cases and headline-only leads in different colors; clickable geolocation list, province filter, month filter and quick client focus. All pins state what their locations mean. Never place an incident at a bank head office merely because its name appears.
4. **Client watchlist:** saved institution names, stage, notes, evidence counts and timeline. Browser localStorage MVP. Authenticated organization workspace required for collaborative use.
5. **Source/provenance:** all snippets link to original report. Separate unverified headline, reported incident, regulator finding, and confirmed financial impact.

## Visual system
Use a calm **white editorial intelligence theme**, blue-grey typography, teal actions, airy spacing, rounded cards, restrained yellow/orange for unverified stories. Dark map is not essential. Strong typography hierarchy and mobile layouts. Accessible focus states and contrasts.

## Design priorities for Replit
- **Import the existing GitHub repository** `khaled-agi/Signal-North`, rather than generating a new unrelated project.
- Preserve the Python collectors, independent `data/*.json` sources and the GitHub Actions schedule.
- Improve responsive layout, sidebar hierarchy, map/list linking and institution evidence cards without changing the meaning of source records.
- Add authenticated multi-user collaboration only in a later phase with a proper backend; do not embed API keys in publicly deployed JavaScript.
- Avoid external tile services that demand an unconfigured key.
- Any improvements should be committed back to the GitHub repository so Pages remains canonical.

## Source classifications
**Regulatory enforcement**: evidence of a published regulatory action, not necessarily customer fraud.
**Reported victim case**: news or police report, including victim claims, bank role, customer financial loss or recovered funds.
**Syndicated headline discovery**: title, publication timestamp, source, headline-only entities and geolocation candidates. Not confirmed wrongdoing.
**CAFC/OBSI aggregated totals**: population-level figures, never banks' direct losses.
**Consulting opportunity**: optional research hypothesis with explicit source and confirmation status, not a conclusion that a client needs assistance.

## Technical release acceptance checks
- Map loads without an API key.
- Search and filters find articles from throughout 2026.
- A mapped article in the right-hand feed opens its corresponding marker.
- Customer fraud losses and regulatory fines are never combined into one statistic.
- Watchlist changes persist in the same browser and CSV export works.
- GitHub Pages deploy succeeds and Chromium browser smoke tests pass.
