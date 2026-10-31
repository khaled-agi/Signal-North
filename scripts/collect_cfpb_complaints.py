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
STATE=DATA/"cfpb_complaints_state.json"
# CFPB's documented 'product' parameter distinguishes bank/account complaints
# from the credit-reporting complaints dominating the generic newest page.
PRODUCT_QUERIES=[
 "Checking or savings account",
 "Credit card",
 "Money transfer, virtual currency, or money service",
 "Mortgage",
 "Vehicle loan or lease",
]
PRODUCT_QUERIES_PER_RUN=3
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
  "company_public_response":text(src.get("company_public_response"),140),
  "submitted_via":text(src.get("submitted_via"),35),
  "date_sent_to_company":valid_date(src.get("date_sent_to_company")),
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

def collect(session=None,clock=None,product=None):
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
 if product is not None:
  if product not in PRODUCT_QUERIES:raise ValueError("unsupported product sample")
  params["product"]=product
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
   "sub_issue","state","company_response","company_public_response",
   "submitted_via","date_sent_to_company","timely","source",
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
 progress=read(STATE,{"next_product_cursor":0})
 cursor=int(progress.get("next_product_cursor",0))%len(PRODUCT_QUERIES)
 chosen=[PRODUCT_QUERIES[(cursor+i)%len(PRODUCT_QUERIES)]
         for i in range(min(PRODUCT_QUERIES_PER_RUN,len(PRODUCT_QUERIES)))]
 health={"last_attempt_at":stamp(clock),"source":"CFPB public Consumer Complaint Database",
   "endpoint":BASE,"status":"not_attempted",
   "sample_limit_per_call":API_PAGE_SIZE,"retention_days":WINDOW_DAYS,
   "methodology":"Bounded rotating published complaint samples, including bank products. NOT a representative sample, findings, or company misconduct rates. No narratives or ZIP codes.",
   "latest_window_total":None,"total_basis":"not_available",
   "requested_product_queries":chosen,"queries":{},
 }
 rows=[]
 offline=os.environ.get("CFPB_OFFLINE")=="1"
 if offline:
  health["status"]="offline_not_scanned"
 else:
  for label,product in [("all_recent",None)]+[(p,p) for p in chosen]:
   try:
    batch,total,start=collect(clock=clock,product=product)
    rows.extend(batch)
    health["queries"][label]={"status":"ok","returned":len(batch),
      "exact_window_total":total,"filter":product or "all products",
      "note":"This is one capped search page, NOT all complaints in category"}
    if product is None:
     health["latest_window_total"]=total
     health["total_basis"]="CFPB exact all-product query total (if supplied); not sampled bank counts" if total is not None else "not_available"
    health["last_success_at"]=stamp(clock)
    health["query_received_from"]=start
   except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
    health["queries"][label]={"status":"error","error_type":type(exc).__name__,
      "filter":product or "all products"}
  ok=sum(q["status"]=="ok" for q in health["queries"].values())
  health["status"]="ok" if ok==len(health["queries"]) else "partial_error" if ok else "error"
  # A failed page shouldn't create a fabricated complaint or aggregate.
  health["returned_in_latest_request"]=len(rows)
  health["queries_succeeded"]=ok
  health["queries_attempted"]=len(health["queries"])
  save(STATE,{"next_product_cursor":(cursor+len(chosen))%len(PRODUCT_QUERIES)})
 merged=retain(old+rows,clock)
 health["stored_records"]=len(merged)
 health["companies_in_stored_sample"]=len(set(x["company"] for x in merged if x.get("company")))
 health["banking_product_records_in_sample"]=sum(x.get("product") in PRODUCT_QUERIES for x in merged)
 save(OUT,{"updated_at":stamp(clock),"source":"CFPB","country_code":"US",
  "complaints":merged,
  "methodology":"Rotating 100-item public complaint search pages across banking products and general results; consumer allegations only. No narratives, ZIPs or PII. Stored counts are NOT national totals, representative samples, institution rankings or verified fraud."})
 save(STATUS,health)
 print(json.dumps({k:health[k] for k in ("status","stored_records","sample_limit_per_call","banking_product_records_in_sample")}))
if __name__=="__main__":run()
