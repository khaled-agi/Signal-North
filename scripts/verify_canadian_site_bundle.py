#!/usr/bin/env python3
"""Fail the deployment when Canadian research UI dependencies are missing."""
from pathlib import Path
import json
import re

root = Path("_site")
page = (root / "index.html").read_text(encoding="utf-8")
scripts = re.findall(r'<script[^>]+src="\./([^"?]+)', page)
missing = [src for src in scripts if not (root / src).is_file()]
required = [
    "data/bank_complaint_disclosures.json",
    "data/canadian_source_registry.json",
    "data/canadian_enforcement_verified.json",
    "data/cafc_aggregates.json",
    "data/cafc_source_status.json",
]
missing += [p for p in required if not (root / p).is_file()]
if missing:
    raise SystemExit("Pages bundle missing referenced assets: " + ", ".join(missing))
for p in required:
    json.loads((root / p).read_text(encoding="utf-8"))
optional_penalties = root / "data/fintrac_penalties_official.json"
if optional_penalties.is_file():
    penalties = json.loads(optional_penalties.read_text(encoding="utf-8"))
    if penalties.get("count", 0) < 15 or penalties["count"] != len(penalties.get("records", [])):
        raise SystemExit("FINTRAC index snapshot incomplete; refusing deployment")
print(f"Pages Canadian bundle verified: {len(scripts)} local scripts, {len(required)} required JSON files")
