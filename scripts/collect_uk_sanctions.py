#!/usr/bin/env python3
"""Download the authoritative, current UK Sanctions List and keep ENTITY entries.

Since January 28 2026 this UK FCDO list is the live UK reference; the old OFSI
Consolidated Asset Freeze Target list is not an actively maintained source.
Sanctions-list entries aren't automatically bank matches or criminal findings.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import tempfile
from datetime import datetime,timezone
from pathlib import Path
import requests

URL="https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv"
DOC="https://www.gov.uk/government/publications/the-uk-sanctions-list"
OUT=Path("data/uk_sanctions_entities.json")
HEALTH=Path("data/uk_sanctions_source_health.json")
MAX_BYTES=75_000_000

def parse_csv(data,minimum=300):
 try:text=data.decode("utf-8-sig")
 except UnicodeDecodeError:text=data.decode("cp1252")
 rows=csv.reader(io.StringIO(text))
 # FCDO CSV has a report date/metadata line before the header.
 header=None
 for i,line in enumerate(rows):
  if i>15:break
  normalized=[x.strip().casefold() for x in line]
  if "unique id" in normalized and "name 6" in normalized:
   header=line
   break
 if not header:raise ValueError("UK Sanctions List CSV header not identified")
 columns={x.strip().casefold():i for i,x in enumerate(header)}
 required=("unique id","name 6","individual, entity, ship","regime name")
 if not all(x in columns for x in required):
  raise ValueError("UK FCDO CSV schema changed")
 def get(row,k):
  pos=columns.get(k,-1)
  return row[pos].strip() if 0<=pos<len(row) else ""
 entries={}
 total=0
 for row in rows:
  if not row:continue
  total+=1
  if get(row,"individual, entity, ship").casefold()!="entity":continue
  uid=get(row,"unique id")
  if not uid:continue
  name=get(row,"name 6")
  if not name:continue
  kind=get(row,"name type")
  # CSV repeats names, addresses and variations. Preserve primary name only;
  # retain the regulator's designation ID as identity, not a string match.
  existing=entries.get(uid)
  priority=kind.casefold().startswith("primary name")
  if existing and not priority:continue
  entry={
   "uk_unique_id":uid[:75],
   "name":name[:350],"name_type":kind[:70] or None,
   "regime":get(row,"regime name")[:250],
   "date_designated":get(row,"date designated")[:70] or None,
   "last_updated":get(row,"last updated")[:70] or None,
   "designation_source":get(row,"designation source")[:120] or None,
   "sanctions_imposed":get(row,"sanctions imposed")[:650] or None,
   "type_of_entity":get(row,"type of entity")[:160] or None,
   "jurisdiction":"UK",
   "source_kind":"UK_FCDO_sanctions_list_entity_designation",
   "source_url":DOC,
   "source_data_url":URL,
   "note":"An entity designation is not a bank identity match, an allegation of bank fraud, or a criminal conviction. Check current UK designation status.",
  }
  entries[uid]=entry
 if total<minimum or len(entries)<minimum:
  raise ValueError(f"Incomplete FCDO CSV: {total} rows, {len(entries)} entity designations")
 return list(entries.values()),total

def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
  json.dump(data,f,ensure_ascii=False,separators=(",",":"))
  staged=f.name
 os.replace(staged,path)

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 health={"last_attempt":now,"source_url":URL}
 if OUT.exists():
  try:
   prior=json.loads(OUT.read_text("utf-8"))
   if prior.get("retrieved_at","")[:10]==now[:10] and os.getenv("SIGNALNORTH_FORCE_UK_SANCTIONS")!="1":
    print("UK FCDO sanctions entity export already current");return
  except (OSError,ValueError):pass
 try:
  with requests.get(URL,timeout=85,stream=True,headers={"Accept":"text/csv","User-Agent":"SignalNorthPublicResearch/1.0"}) as response:
   response.raise_for_status()
   parts=[];size=0
   for block in response.iter_content(65536):
    size+=len(block)
    if size>MAX_BYTES:raise ValueError("UK sanctions CSV exceeds download cap")
    parts.append(block)
  binary=b"".join(parts)
  records,total=parse_csv(binary)
  atomic(OUT,{
   "source":"United Kingdom Foreign, Commonwealth & Development Office",
   "source_url":DOC,"raw_file":URL,
   "retrieved_at":now,"sha256":hashlib.sha256(binary).hexdigest(),
   "record_count":len(records),"raw_name_rows":total,"records":records,
   "methodology":"Current UK Sanctions List only. Entity designations deduplicated by the regulator's Unique ID; natural persons/ships excluded. This is not a record of bank wrongdoing or sanctions history.",
  })
  health.update({"status":"success","last_success":now,"record_count":len(records),"raw_rows":total})
  print(f"UK FCDO current entity designations: {len(records)} from {total} original CSV rows",flush=True)
 except Exception as e:
  health.update({"status":"failed_last_good_preserved" if OUT.exists() else "unavailable",
                 "error_type":type(e).__name__,"detail":str(e)[:180]})
  print("UK FCDO import FAILED:",type(e).__name__,str(e)[:160],flush=True)
 atomic(HEALTH,health)
if __name__=="__main__":main()
