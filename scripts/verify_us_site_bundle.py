#!/usr/bin/env python3
"""Fail closed when public U.S. directory or lifecycle datasets are incomplete."""
from pathlib import Path
import json

root=Path("_site/data")
requirements={
 "us_fdic_institutions.json":("records",2500,"fdic_cert"),
 "us_fdic_failures.json":("records",3500,None),
 "us_ncua_credit_unions.json":("records",3500,"ncua_charter"),
}
for filename,(key,minimum,unique_key) in requirements.items():
 path=root/filename
 if not path.is_file():
  raise SystemExit("Required official U.S. dataset not packaged: "+filename)
 d=json.loads(path.read_text("utf-8"))
 rows=d.get(key,[])
 if not isinstance(rows,list) or len(rows)<minimum or d.get("record_count")!=len(rows):
  raise SystemExit(f"{filename}: invalid size or declared count, got {len(rows)}")
 if unique_key:
  ids=[r.get(unique_key) for r in rows]
  if any(not x for x in ids) or len(set(ids))!=len(ids):
   raise SystemExit(f"{filename}: missing or repeated entity identifiers")
 if any(r.get("country")!="US" for r in rows):
  raise SystemExit(f"{filename}: foreign country in U.S. directory")
 print(f"Validated {filename}: {len(rows)} official rows")
for filename in ("us_fdic_source_health.json","us_ncua_source_health.json","us_regulatory_signal_publications.json"):
 if not (root/filename).exists():
  raise SystemExit("Missing explicit source health/signal: "+filename)
 json.loads((root/filename).read_text("utf-8"))
print("U.S. identity and source status bundles verified")
