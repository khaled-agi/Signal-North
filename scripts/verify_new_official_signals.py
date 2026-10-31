#!/usr/bin/env python3
"""Validate any actually collected OCC/OFAC/SEC snapshots before publication.

If a source is blocked, its health status is published separately. We never
substitute 0 for a failed source or label unreviewed releases as final orders.
"""
from pathlib import Path
import json
root=Path("_site/data")
specs={
 "us_occ_enforcement_actions.json":("records",20,"id"),
 "us_ofac_sdn_entities.json":("records",5000,"ofac_ent_num"),
 "us_sec_litigation_releases.json":("records",3,"id"),
 "uk_sanctions_entities.json":("records",300,"uk_unique_id"),
}
for file,(list_key,minimum,id_key) in specs.items():
 path=root/file
 if not path.exists():
  print(f"::warning::{file}: collector did not return a validated snapshot; source health must explain failure")
  continue
 d=json.loads(path.read_text("utf-8"))
 records=d.get(list_key)
 if not isinstance(records,list) or len(records)<minimum or d.get("record_count")!=len(records):
  raise SystemExit(f"Invalid source snapshot: {file}")
 ids=[r.get(id_key) for r in records]
 if any(not x for x in ids) or len(ids)!=len(set(ids)):
  raise SystemExit(f"Missing or repeated source IDs in {file}")
 print(f"Validated {file}: {len(records)} original-source records")
for h in ("us_occ_enforcement_health.json","us_ofac_source_health.json","us_sec_source_health.json","uk_sanctions_source_health.json"):
 path=root/h
 if not path.exists():raise SystemExit(f"Missing required source-health disclosure: {h}")
 d=json.loads(path.read_text("utf-8"))
 if not (d.get("status") or d.get("source_health")):raise SystemExit(f"Empty source status: {h}")
print("New regulator source health verified; unavailable sources are explicitly labeled.")
