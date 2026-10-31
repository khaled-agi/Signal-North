#!/usr/bin/env python3
"""Collect original OCC enforcement-action records via the official OCC Data API.

Bank names searched here are discovery terms; the API's charter number is
preserved. Action on an individual is *not* an enforcement finding against
the related institution. The API's public DEMO_KEY may rate-limit requests.
"""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote
import requests

BASE="https://api.occ.gov/EnforcementActions/list/"
SEARCH_TERMS=(
 "JPMorgan","Wells Fargo","Citibank","Bank of America","U.S. Bank",
 "PNC","Capital One","TD Bank","HSBC","BMO","Fifth Third",
 "Truist","Santander","KeyBank","Regions Bank","M&T Bank",
 "Citizens Bank","Huntington","Discover Bank","First National Bank",
 "Bank of New York","State Street","American Express","Comerica",
)
OUT=Path("data/us_occ_enforcement_actions.json")
HEALTH=Path("data/us_occ_enforcement_health.json")
MIN_VALID=20
MAX_RESPONSE_BYTES=5_000_000

def parse_amount(value):
 value=str(value or "").replace("$","").replace(",","").strip()
 try:
  amount=Decimal(value)
  return float(amount) if amount.is_finite() and amount>=0 else None
 except InvalidOperation:
  return None

def to_date(value):
 from datetime import datetime
 value=str(value or "").strip()
 if not value or value=="N/A":return None
 for fmt in ("%m/%d/%Y","%Y-%m-%d"):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 return None

def normalize(raw):
 name=str(raw.get("Institution") or raw.get("Company") or "").strip()
 if not name:return None
 charter=str(raw.get("CharterNumber") or "").strip() or None
 individual=str(raw.get("Individual") or "").strip() or None
 docket=str(raw.get("DocketNumber") or "").strip() or None
 action=str(raw.get("TypeCode") or "").strip()
 if not action:return None
 date=to_date(raw.get("StartDate"))
 start_docs=[str(x).strip() for x in raw.get("StartDocuments",[]) if str(x).strip() not in ("","N/A")][:15]
 termination_docs=[str(x).strip() for x in raw.get("TerminationDocuments",[]) if str(x).strip() not in ("","N/A")][:15]
 key="|".join([charter or "",name,individual or "",docket or "",date or "",action,*start_docs])
 ident=hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
 return {
  "id":ident,"agency":"OCC","jurisdiction":"US","institution":name[:250],
  "occ_charter":charter,"individual_party":individual,
  "subject_is_individual":bool(individual),
  "case_type":action,"action_description":str(raw.get("TypeDescription") or "").strip()[:250],
  "start_date":date,"termination_date":to_date(raw.get("TerminationDate")),
  "docket":docket,"start_documents":start_docs,"termination_documents":termination_docs,
  "amount_usd":parse_amount(raw.get("Amount")),
  "amount_raw":str(raw.get("Amount") or "").strip()[:60],
  "subject_matters":[str(x)[:120] for x in raw.get("SubjectMatters",[]) if x][:30],
  "source_url":"https://apps.occ.gov/EASearch",
  "original_api":"https://api.occ.gov/EnforcementActions/list",
  "source_kind":"OCC_official_enforcement_action_data",
  "interpretation":"The action type and subject party govern legal interpretation. Individual actions are not institutional findings; terminated orders may no longer apply.",
 }

def collect_one(session,term,key):
 url=BASE+quote(term,safe="")
 response=session.get(url,params={"api_key":key},headers={"Accept":"application/json","User-Agent":"SignalNorthResearch/1.0 (official OCC bank enforcement research)"},timeout=35)
 response.raise_for_status()
 if len(response.content)>MAX_RESPONSE_BYTES:raise ValueError("OCC response size unexpected")
 data=response.json()
 if not isinstance(data,list):raise ValueError("OCC API returned unexpected schema")
 if len(data)>20000:raise ValueError("OCC query results exceed safe capacity")
 return [n for x in data if isinstance(x,dict) if (n:=normalize(x))]

def atomic(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as tmp:
  json.dump(obj,tmp,ensure_ascii=False,separators=(",",":"))
  name=tmp.name
 os.replace(name,path)

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 old={"records":[],"source_health":{}}
 if OUT.exists():
  try:old=json.loads(OUT.read_text(encoding="utf-8"))
  except (OSError,ValueError):pass
 health=dict(old.get("source_health",{}))
 records={x["id"]:x for x in old.get("records",[])}
 key=os.getenv("OCC_API_KEY") or "DEMO_KEY"
 budget=int(os.getenv("OCC_SEARCH_BATCH","12"))
 if budget<1 or budget>len(SEARCH_TERMS):raise ValueError("OCC_SEARCH_BATCH invalid")
 session=requests.Session()
 start=int(old.get("next_offset",0))%len(SEARCH_TERMS)
 sampled=[SEARCH_TERMS[(start+i)%len(SEARCH_TERMS)] for i in range(budget)]
 succeeded=0
 for term in sampled:
  try:
   items=collect_one(session,term,key)
   if len(items)==0:raise ValueError("zero results returned for broad search term")
   for x in items:records[x["id"]]=x
   succeeded+=1
   health[term]={"status":"success","last_success":now,"returned":len(items)}
   print(f"OCC {term}: {len(items)} original action records",flush=True)
  except Exception as e:
   health[term]={"status":"failed_last_good_preserved" if old.get("records") else "unavailable",
                 "last_attempt":now,"error_type":type(e).__name__,"detail":str(e)[:160]}
   print(f"OCC {term}: {type(e).__name__}",flush=True)
  time.sleep(0.2)
 # Never publish a partial results list as a complete official dataset.
 if len(records)>=MIN_VALID:
  atomic(OUT,{
   "source":"OCC Enforcement Actions Data API",
   "source_url":"https://api.occ.gov/",
   "methodology":"Partial, rotating bank-name discovery, not a full OCC enforcement database. Individuals, institution orders, monetary penalties and ended orders remain distinct. Name mentions do not prove bank wrongdoing.",
   "retrieved_at":now,"record_count":len(records),"records":list(records.values()),
   "source_health":health,"next_offset":(start+budget)%len(SEARCH_TERMS),
   "search_term_coverage":len([x for x in health.values() if x.get("status")=="success"]),
   "total_search_terms":len(SEARCH_TERMS),
  })
 atomic(HEALTH,{"updated_at":now,"source_url":"https://api.occ.gov/",
   "successful_queries_this_run":succeeded,"tested_queries":sampled,
   "count":len(records),"source_health":health,
   "status":"success" if len(records)>=MIN_VALID else "failed_last_good_preserved" if OUT.exists() else "unavailable"})
 print(f"OCC original action snapshot: {len(records)} records, {succeeded}/{len(sampled)} successful searches",flush=True)

if __name__=="__main__":main()
