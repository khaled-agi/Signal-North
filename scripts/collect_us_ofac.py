#!/usr/bin/env python3
"""Official OFAC SDN business/entity sanctions designations (not name matches).

Fetches Treasury's headerless sdn.csv; retains entity/group rows only.
Natural persons, aircraft, vessels excluded from Signal North's enterprise
coverage; no names automatically joined to FDIC or Canadian banks.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import datetime,timezone
from pathlib import Path
import requests

# Treasury moved SDN downloads to the Sanctions List Service (2024). The legacy
# treasury.gov path now redirects or serves HTML, which parsed as 1-column rows.
URLS=(
 "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
 "https://www.treasury.gov/ofac/downloads/sdn.csv",
)
URL=URLS[0]
OUT=Path("data/us_ofac_sdn_entities.json")
HEALTH=Path("data/us_ofac_source_health.json")
MAX_BYTES=20_000_000
# Headerless legacy SDN CSV: ent_num, name, type, program, title, callsign,
# vessel_type, tonnage, grt, vessel_flag, vessel_owner, remarks.
NULL="-0-"

def parse(data, minimum=5000):
 try:
  text=data.decode("utf-8-sig")
 except UnicodeDecodeError:
  text=data.decode("cp1252")
 reader=csv.reader(io.StringIO(text))
 all_ids=set()
 records=[]
 total=0
 excluded={}
 for row in reader:
  # The SDN export ends with a lone EOF control character (\x1a); skip blank,
  # whitespace-only or control-character-only trailer rows.
  if not row or not "".join(row).strip(" \t\r\n\x1a\x00"):continue
  if text.lstrip()[:15].lower().startswith(("<!doctype","<html")):
   raise ValueError("OFAC endpoint returned HTML instead of CSV")
  total+=1
  if len(row)!=12:raise ValueError(f"Unexpected OFAC SDN row columns: {len(row)}")
  ent,name,kind,program,*remainder=row
  ent=ent.strip();name=name.strip()
  if not ent.isdigit() or not name:raise ValueError("OFAC SDN row lacks official id/name")
  if ent in all_ids:raise ValueError("Duplicate OFAC sanctions list ID")
  all_ids.add(ent)
  kind=kind.strip().casefold()
  if kind not in ("",NULL,"entity"):
   excluded[kind]=excluded.get(kind,0)+1
   continue
  programs=re.findall(r"\[([^\]]+)\]",program)
  if not programs and program and program!=NULL:
   programs=[program]
  records.append({
   "ofac_ent_num":ent,"name":name[:350],"listed_type":"organization_or_group",
   "sanctions_programs":programs[:30],
   "original_type":kind or NULL,
   "source_kind":"OFAC_SDN_official_list_designation",
   "jurisdiction":"US",
   "source_url":"https://ofac.treasury.gov/sanctions-list-service",
   "source_data_url":URL,
   "scope_note":"OFAC designation, not necessarily a financial institution. Entity naming alone must never be treated as a confirmed match to another legal person.",
  })
 if len(records)<minimum or total<minimum:
  raise ValueError(f"Unusually small OFAC SDN dataset: {len(records)} organizations / {total} rows")
 return records,{"all_sdn_rows":total,"entity_rows":len(records),"excluded_types":excluded}

def atomic(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as f:
  json.dump(obj,f,ensure_ascii=False,separators=(",",":"))
  tmp=f.name
 os.replace(tmp,path)

def download(url):
 r=requests.get(url,timeout=90,stream=True,allow_redirects=True,
                headers={"User-Agent":"SignalNorthPublicResearch/1.0 (+https://github.com/khaled-agi/Signal-North)","Accept":"text/csv,*/*"})
 r.raise_for_status()
 chunks=[];size=0
 for part in r.iter_content(65536):
  size+=len(part)
  if size>MAX_BYTES:raise ValueError("OFAC file exceeds safe capacity")
  chunks.append(part)
 return b"".join(chunks)

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text("utf-8"))
   if old.get("retrieved_at","")[:10]==now[:10] and os.getenv("SIGNALNORTH_FORCE_OFAC")!="1":
    print("OFAC current validated snapshot already collected today");return
  except (ValueError,OSError):pass
 health={"source_url":URL,"last_attempt":now}
 try:
  errors=[]
  for url in URLS:
   try:
    binary=download(url)
    records,stats=parse(binary)
    health["source_url"]=url
    break
   except Exception as exc:
    errors.append(f"{url}: {type(exc).__name__}: {str(exc)[:120]}")
  else:
   raise ValueError(" | ".join(errors)[:400])
  atomic(OUT,{
   "source":"U.S. Treasury Office of Foreign Assets Control / SDN List",
   "source_url":health["source_url"],"retrieved_at":now,"sha256":hashlib.sha256(binary).hexdigest(),
   "record_count":len(records),"source_stats":stats,
   "methodology":"Only source-listed organization/group entries (not people, vessels, or aircraft). Does NOT infer financial-sector status, criminal convictions, or automatic bank matches. Current list only, not a history of additions/removals.",
   "records":records,
  })
  health.update({"status":"success","last_success":now,"record_count":len(records),"source_stats":stats})
  print("OFAC verified organizations/groups:",len(records),flush=True)
 except Exception as e:
  health.update({"status":"failed_last_good_preserved" if OUT.exists() else "unavailable","error_type":type(e).__name__,"detail":str(e)[:180]})
  print("OFAC collector failed:",type(e).__name__,str(e)[:150],flush=True)
 atomic(HEALTH,health)

if __name__=="__main__":main()
