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
    "data/obsi_annual_banking.json",
    "data/obsi_firm_complaints.json",
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
obsi = json.loads((root / "data/obsi_annual_banking.json").read_text(encoding="utf-8"))
if len(obsi.get("rows", [])) < 5:
    raise SystemExit("OBSI banking historical series is missing")
banks = json.loads((root / "data/bank_complaint_disclosures.json").read_text(encoding="utf-8"))
if len(banks.get("records", [])) < 15:
    raise SystemExit("Bank disclosure archive is incomplete")
firm = json.loads((root / "data/obsi_firm_complaints.json").read_text(encoding="utf-8"))
if len(firm.get("records", [])) < 91:
    raise SystemExit("OBSI firm-level source rows missing")
for measure, reported in [("complaints_received", 6329),("opened_cases",5375),("closed_cases",4373),("resolved_satisfaction",1051)]:
    fy2025 = [r for r in firm["records"] if r.get("fiscal_year") == 2025]
    if sum(r.get(measure,0) for r in fy2025)!=reported:
        raise SystemExit("OBSI FY2025 totals mismatch: "+measure)
fy2024 = [r for r in firm["records"] if r.get("fiscal_year") == 2024]
if len(fy2024) != 38:
    raise SystemExit("OBSI FY2024 firm rows missing")
for metric,total in [("complaints_received",2527),("complaints_deemed_in_mandate",2445),("opened_cases",2504)]:
    if sum(r.get(metric,0) for r in fy2024)!=total:
        raise SystemExit("OBSI FY2024 report mismatch: "+metric)
print(f"Pages Canadian bundle verified: {len(scripts)} local scripts, {len(required)} required JSON files")
