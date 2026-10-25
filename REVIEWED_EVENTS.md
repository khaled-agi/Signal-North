# Reviewed Event Database — Editorial Standard

Signal North distinguishes **reported cases**, **reviewed source evidence**, and **independently established facts**.

## What is presently published

The initial reviewed-event database imports six legacy source-attributed case summaries from \`data/incidents.json\`. Those are journalist / police / government sourced accounts; **they have NOT been independently adjudicated or independently re-investigated by Signal North**. Each record is labelled \`source_reviewed\` and \`independently_verified: false\`. Where prior records do not specify who reviewed them or when, the fields remain null instead of inventing credentials.

\`data/reviewed_events.json\` is *generated*. Do not edit it. The seed remains \`data/incidents.json\`. Future approved additions belong in \`data/reviewed_events_editorial.json\` and must pass the validation rules described below.

## Required record structure

A reviewed event requires:

- Unique event ID, neutral title, publication date and incident period when known.
- A list of **public original sources**, with stable source IDs, URL, publisher, publication date and document type. Do not republish copyrighted article bodies.
- **Atomic claims** stating what each publication reports. Every claim references one or more source IDs. State whether it is *source attributed* or *officially reported*; if a claim conflicts between publications, list the difference explicitly instead of reconciling it by guess.
- A **reported timeline**, with each step tied to source IDs. No fabricated incident dates or transactional sequences.
- **Institution relationships** with explicit roles: impersonated institution, affected customer's account provider, investigated subject, recovering institution or regulator. Mentioned in a headline is a different role; never infer wrongdoing, guilt, or control failure.
- **Financial impact types** such as customer-reported loss, exposure, recovered funds, bank-borne loss or regulator penalty. Do not total incompatible impact types or attribute victim losses to a bank.
- **Geographic role**: report source location, customer city, alleged incident location or undetermined. Unknown does not default to bank headquarters.
- **Unanswered questions**, contradictions and evidence-gaps. Absence of evidence isn't evidence of absence.
- **Reviewer audit trail** for any new editorial event: reviewer identifier, actual review date, and a concrete rationale grounded in public sources.

## Hard review gate

\`scripts/build_reviewed_events.py\` creates output only from previously curated seed cases and records explicitly marked \`editorially_approved\` with a reviewer ID, date, and review rationale. Every claim, timeline step, amount and institution role needs a valid source reference. Missing or unsupported statements cause the build to fail.

The database **never automatically imports headlines, similarity clusters, suggested cross-report links, community tips, or generated AI text**. Reviewer-approved links to reporting groups require an explicit rationale and source references. All group IDs must exist in the published article archive.

\`data/event_review_candidates.json\` contains suggested relationships *for review*, not an event database. These pairs are intended for a research inbox so an editor can open the two original stories and decide whether they are truly about the same incident.

## How to add an event

1. Investigate the original sources; determine which claims each source actually supports.
2. Add an event object to \`data/reviewed_events_editorial.json\`, with \`review_state: "editorially_approved"\`, \`independently_verified: false\`, reviewer ID, ISO review date and review rationale.
3. List every original source, then link atomic claims, financial amounts, timeline entries, institutions and any reporting group links back to those source IDs.
4. If there are discrepancies between sources, preserve them in \`counterevidence\` and write an evidence-gap question.
5. Run \`python scripts/build_reviewed_events.py\`, \`python -m unittest discover -s tests -p 'test_logic.py'\`, and the browser smoke suite.
6. Submit the source and evidence change as a reviewed GitHub pull request; do not accept automated or anonymous submissions as verified case material.

## Avoid

Naming private victims, bank account numbers, customer financial records, speculative guilt ratings, fabricated dates, fabricated bank losses, unverified social allegations, automated promotions of article matches to factual case records. For legal changes (charges, appeals, settlements or dismissal), preserve as-of dates and procedural status.

This is a *public-source research database*, not a law-enforcement incident database or a confidential investigation tool.
