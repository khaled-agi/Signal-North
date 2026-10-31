#!/usr/bin/env python3
"""Collect structured notices from FINTRAC's official public penalty table.

Source-level statements are preserved; this is an index snapshot, not a court finding.
A failed/incomplete response never replaces the last valid published data.
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://fintrac-canafe.canada.ca/pen/4-eng"
OUTPUT = Path("data/fintrac_penalties_official.json")
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
PENALTY = re.compile(r"administrative monetary penalty of\s*\$\s*([\d,]+(?:\.\d+)?)", re.I)
VIOLATIONS = re.compile(r"for committing\s+([\d,]+)\s+(?:violations?|contraventions?)", re.I)


def parse_html(html, minimum=15):
    soup = BeautifulSoup(html, "html.parser")
    records, seen = [], set()
    for tr in soup.select("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) < 2:
            continue
        published_match = DATE.search(cells[0].get_text(" ", strip=True))
        body = " ".join(cells[1].get_text(" ", strip=True).split())
        amount_match = PENALTY.search(body)
        if not published_match or not amount_match or len(body) < 90:
            continue
        published = published_match.group()
        amount = float(amount_match.group(1).replace(",", ""))
        violation_match = VIOLATIONS.search(body)
        if amount <= 0:
            continue
        name = re.split(
            r",\s+(?:also operating as|formerly known as|a\s|an\s|which\s)"
            r"|\s+was imposed an administrative monetary penalty",
            body, maxsplit=1, flags=re.I,
        )[0].strip(" ,.")
        if len(name) < 4 or len(name) > 200:
            name = None
        row_id = hashlib.sha256((published + "|" + body).encode()).hexdigest()[:20]
        if row_id in seen:
            continue
        seen.add(row_id)
        link = cells[1].find("a", href=True)
        href = link.get("href", "") if link else ""
        # Use only the official index unless a direct notice URL is explicit.
        source_url = URL
        if href.startswith("https://fintrac-canafe.canada.ca/pen/"):
            source_url = href
        appeal = bool(re.search(r"\b(?:has appealed|appealed the|filed a notice of appeal)\b", body, re.I))
        paid = bool(re.search(r"\b(?:paid.*in full|penalty has been paid|proceedings have ended)\b", body, re.I))
        status = "appealed_or_appeal_reported" if appeal and not paid else (
            "paid_or_proceedings_ended" if paid else "not_confirmed"
        )
        records.append({
            "record_id": row_id, "agency": "FINTRAC", "published": published,
            "entity_name": name, "penalty_cad": amount,
            "violation_count": int(violation_match.group(1).replace(",", "")) if violation_match else None,
            "status_summary": status, "source_text": body, "source_url": source_url,
            "source_kind": "official_public_notice_index",
        })
    if len(records) < minimum:
        raise ValueError(f"Unexpected FINTRAC index size {len(records)} (< {minimum}); retaining prior data")
    return records


def main():
    r = requests.get(URL, timeout=45, headers={"User-Agent": "SignalNorthResearch/1.0 (public enforcement index)", "Accept": "text/html"})
    r.raise_for_status()
    if len(r.content) > 4_000_000:
        raise ValueError("FINTRAC page exceeds the validated 4MB input limit")
    records = parse_html(r.text)
    result = {
        "source_url": URL, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records), "scope": "Official FINTRAC public penalty index; notices generally retained for five years.",
        "caveat": "These are penalty notices, not confirmed criminal offences. A named entity's appeal and payment status can change. The latest source text is retained for review.",
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=OUTPUT.parent, encoding="utf-8", delete=False) as tmp:
        json.dump(result, tmp, ensure_ascii=False, separators=(",", ":"))
        temp_name = tmp.name
    os.replace(temp_name, OUTPUT)
    print(f"Validated {len(records)} structured FINTRAC public penalty notices")


if __name__ == "__main__":
    main()
