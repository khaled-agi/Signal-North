#!/usr/bin/env python3
"""Public CFPB complaint metadata, one bounded original-source integration.

Only published categorical fields are retained. No narratives, ZIP codes,
personal details, attachment links or raw API responses are persisted.
Records are consumer ALLEGATIONS, not verified facts or regulator findings.
"""
from __future__ import annotations
import json,os,re
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"cfpb_complaints.json"
STATUS=DATA/"cfpb_complaints_status.json"
BASE="https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
DATABASE="https://www.consumerfinance.gov/data-research/consumer-complaints/"
API_PAGE_SIZE=100 # CFPB documented per-request maximum
WINDOW_DAYS=90
MAX_RECORDS=2500

def utcnow():return datetime.now(timezone.utc)
def stamp(dt=None):return (dt or utcnow()).isoformat(timespec="seconds")
def read(path,default):
 try:return json.loads(path.read_text("utf-8"))
 except (FileNotFoundError,json.JSONDecodeError):return default
def save(path,record):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def text(value,limit=200):
 return " ".join(value.split())[:limit] if isinstance(value,str) else ""
def valid_date(value):
 if not isinstance(value,str):return None
 raw=value[:10]
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",raw):return None
 try:datetime.strptime(raw,"%Y-%m-%d")
 except ValueError:return None
 return raw
def record(hit):
 """Explicit allowlist to avoid publishing complaint narratives/PII by accident."""
 src=hit.get("_source") if isinstance(hit,dict) else None
 if not isinstance(src,dict):return None
 cid=src.get("complaint_id",hit.get("_id"))
 if not str(cid).isdigit() or not (0<int(cid)<10**10):return None
 date=valid_date(src.get("date_received"))
 if not date:return None
 return {
  "id":str(int(cid)),
  "date_received":date,
  "company":text(src.get("company"),180),
  "product":text(src.get("product"),150),
  "sub_product":text(src.get("sub_product"),150),
  "issue":text(src.get("issue"),180),
  "sub_issue":text(src.get("sub_issue"),180),
  "state":text(src.get("state"),5),
  "company_response":text(src.get("company_response"),100),
  "timely":text(src.get("timely"),12),
  "source":"CFPB Consumer Complaint Database",
  "source_url":BASE+str(int(cid)),
  "evidence_status":"published_consumer_complaint_not_verified",
  "geography_basis":"consumer_reported_state_not_incident_location",
 }
def unpack(body):
 if not isinstance(body,dict):raise ValueError("response is not an object")
 hits=body.get("hits")
 if not isinstance(hits,dict) or not isinstance(hits.get("hits"),list):
  raise ValueError("missing complaint hits; API response changed")
 rows=[x for item in hits["hits"] if (x:=record(item)) is not None]
 total=hits.get("total")
 if isinstance(total,dict):
  raw=total.get("value")
  total_count=raw if isinstance(raw,int) and raw>=0 and total.get("relation")=="eq" else None
 elif isinstance(total,int):total_count=total if total>=0 else None
 else:total_count=None
 return rows,total_count

def collect(session=None,clock=None):
 session=session or requests.Session()
 clock=clock or utcnow()
 start=(clock-timedelta(days=WINDOW_DAYS)).date().isoformat()
 params={
  "size":API_PAGE_SIZE,
  "sort":"created_date_desc",
  "date_received_min":start,
  "no_aggs":"true",
  "no_highlight":"true",
 }
 response=session.get(BASE,params=params,headers={
   "User-Agent":"SignalNorthResearch/1.0 (+https://github.com/khaled-agi/Signal-North)",
   "Accept":"application/json",
  },timeout=35)
 response.raise_for_status()
 if len(response.content)>3_000_000:raise ValueError("CFPB response unusually large")
 body=response.json()
 return (*unpack(body),start)

def retain(rows,clock=None):
 clock=clock or utcnow()
 cutoff=(clock-timedelta(days=WINDOW_DAYS)).date().isoformat()
 by_id={}
 for item in rows:
  if not isinstance(item,dict):continue
  # Defensively reconstruct from known public categorical fields only.
  if item.get("evidence_status")!="published_consumer_complaint_not_verified":continue
  cid=str(item.get("id",""))
  dt=valid_date(item.get("date_received"))
  if not cid.isdigit() or not dt or dt<cutoff or dt>clock.date().isoformat():continue
  cleaned={k:item.get(k,"") for k in (
   "id","date_received","company","product","sub_product","issue",
   "sub_issue","state","company_response","timely","source",
   "source_url","evidence_status","geography_basis")}
  cleaned["source_url"]=BASE+cid
  cleaned["source"]="CFPB Consumer Complaint Database"
  cleaned["evidence_status"]="published_consumer_complaint_not_verified"
  cleaned["geography_basis"]="consumer_reported_state_not_incident_location"
  by_id[cid]=cleaned
 return sorted(by_id.values(),key=lambda r:(r["date_received"],int(r["id"])),reverse=True)[:MAX_RECORDS]

def run():
 clock=utcnow()
 previous=read(OUT,{"complaints":[]})
 old=retain(previous.get("complaints",[]),clock)
 # Never turn offline tests or API errors into fabricated complaint totals.
 health={"last_attempt_at":stamp(clock),"source":"CFPB public Consumer Complaint Database",
   "endpoint":BASE,"status":"not_attempted",
   "sample_limit_per_call":API_PAGE_SIZE,"retention_days":WINDOW_DAYS,
   "methodology":"Only recent, published categorical complaint metadata; not a population sample, findings, fraud incidents, bank losses or regulator enforcement.",
   "latest_window_total":None,
   "total_basis":"not_available",
 }
 rows=[]
 if os.environ.get("CFPB_OFFLINE")=="1":
  health["status"]="offline_not_scanned"
 else:
  try:
   rows,total,start=collect(clock=clock)
   health.update({"status":"ok" if rows else "empty_response",
     "last_success_at":stamp(clock),"query_received_from":start,
     "returned_in_latest_request":len(rows),
     "latest_window_total":total,
     "total_basis":"CFPB API exact search total, not sampled rows" if total is not None else "not_available"})
  except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
   health.update({"status":"error","error_type":type(exc).__name__})
 merged=retain(old+rows,clock)
 health["stored_records"]=len(merged)
 save(OUT,{"updated_at":stamp(clock),"source":"CFPB","country_code":"US",
  "complaints":merged,
  "methodology":"Bounded recent CFPB public complaint records; consumer allegations, not validated misconduct. Company/issue/state reflect CFPB categorizations; no narratives, ZIPs or personal details. Counts over stored records are not national totals."})
 save(STATUS,health)
 print(json.dumps({k:health[k] for k in ("status","stored_records","sample_limit_per_call")}))
if __name__=="__main__":run()
