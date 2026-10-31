#!/usr/bin/env python3
"""Aggregate public CAFC open-government fraud reports without publishing records.

Unlike CFPB, this is Canadian fraud-reporting intake, NOT institution complaints.
Read official RCMP/CAFC CSV in bounded streaming mode. Drop report IDs and
individual-level details; retain only aggregate yearly/geographic/theme data.
"""
from __future__ import annotations
import csv,io,json,os,re,tempfile
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests

DATA=Path(__file__).resolve().parents[1]/"data"
OUT=DATA/"cafc_aggregates.json"
STATUS=DATA/"cafc_source_status.json"
SOURCE_URL=("https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f/"
 "resource/43c67af5-e598-4a9b-a484-fe1cb5d775b5/download/"
 "cafc-open-gouv-database-2021-01-01-to-2025-09-30-extracted-2025-10-01.csv")
SOURCE_PAGE="https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f"
SOURCE_LABEL="Royal Canadian Mounted Police / Canadian Anti-Fraud Centre"
MIN_CELL=5
MAX_BYTES=105_000_000
REFRESH_DAYS=7
EXPECTED_LAST_DATE="2025-09-30"

def now():return datetime.now(timezone.utc)
def iso(t=None):return (t or now()).isoformat(timespec="seconds")
def read(path,default):
 try:return json.loads(path.read_text("utf-8"))
 except (OSError,ValueError):return default
def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n","utf-8")
def norm(s):
 return re.sub(r"[^a-z0-9]+","",str(s).lower())
def col(headers,terms):
 known={norm(x):x for x in headers if x}
 for term in terms:
  v=norm(term)
  if v in known:return known[v]
 for term in terms:
  v=norm(term)
  for k,orig in known.items():
   if k.startswith(v):return orig
 return None
def amount(raw):
 """Interpret only nonnegative numeric loss values; never fabricate negatives."""
 if raw is None:return None
 v=str(raw).strip().replace("\u00a0","").replace(" ","")
 if not v:return None
 v=v.replace("$","").replace(",","")
 if not re.fullmatch(r"\d+(?:\.\d{1,2})?",v):return None
 try:result=round(float(v),2)
 except ValueError:return None
 return result if result<1e14 else None
def positive_int(raw):
 v=str(raw or "").strip().replace(",","")
 return int(v) if v.isdigit() and int(v)<1000000 else None
def datepart(raw):
 s=str(raw or "").strip()
 if re.match(r"^\d{4}-\d{2}-\d{2}",s):
  d=s[:10]
  try:datetime.strptime(d,"%Y-%m-%d")
  except ValueError:return None
  return d
 for template in ("%m/%d/%Y","%Y/%m/%d","%d/%m/%Y"):
  try:return datetime.strptime(s[:10],template).strftime("%Y-%m-%d")
  except ValueError:pass
 return None
def aggregate(fileobj):
 """Only province/year/category/method aggregates; no raw complaint ID output."""
 reader=csv.DictReader(fileobj)
 headers=reader.fieldnames or []
 fields={
  "date":col(headers,["Date Received","Date recue"]),
  "country":col(headers,["Country","Pays"]),
  "province":col(headers,["Province/State","Province/Etat"]),
  "category":col(headers,["Fraud and Cybercrime Thematic Categories"]),
  "method":col(headers,["Solicitation Method"]),
  "victims":col(headers,["Number of Victims"]),
  "loss":col(headers,["Dollar Loss","Dollar Loss/pertes financieres"]),
 }
 if any(not fields[k] for k in ("date","country","province","category","method","loss")):
  raise ValueError("CAFC column schema is missing required fields: "+
   ",".join(k for k,v in fields.items() if not v))
 counts=defaultdict(lambda: [0,0,0.0,0,0])
 tally={"rows_read":0,"canada_rows":0,"outside_canada_rows":0,"invalid_date":0,
        "missing_province":0,"missing_loss":0,"missing_category":0}
 def update(bucket,kind,year,name,province,loss,victims):
  key=(kind,year,name,province)
  current=bucket[key]
  current[0]+=1
  if victims is not None:current[1]+=victims
  if loss is not None:current[2]+=loss
  if loss is None:current[3]+=1
  if victims is None:current[4]+=1
 for row in reader:
  tally["rows_read"]+=1
  if str(row.get(fields["country"]) or "").strip().casefold() not in ("canada","canadá"):
   tally["outside_canada_rows"]+=1
   continue
  received=datepart(row.get(fields["date"]))
  if not received or not ("2021"<=received[:4]<="2026"):
   tally["invalid_date"]+=1;continue
  year=received[:4]
  province=str(row.get(fields["province"]) or "").strip()[:70] or "Not specified"
  category=str(row.get(fields["category"]) or "").strip()[:150] or "Not specified"
  method=str(row.get(fields["method"]) or "").strip()[:100] or "Not specified"
  if province=="Not specified":tally["missing_province"]+=1
  if category=="Not specified":tally["missing_category"]+=1
  loss=amount(row.get(fields["loss"]))
  if loss is None:tally["missing_loss"]+=1
  victims=positive_int(row.get(fields["victims"])) if fields["victims"] else None
  tally["canada_rows"]+=1
  update(counts,"year",year,"Canada","",loss,victims)
  update(counts,"category",year,category,"",loss,victims)
  update(counts,"province",year,province,"",loss,victims)
  update(counts,"method",year,method,"",loss,victims)
  # Cross-category provincial summary; low-count cells are suppressed.
  update(counts,"province_category",year,category,province,loss,victims)
 out=[]
 for (kind,year,name,province),(n,victims,loss,missing_loss,missing_victims) in counts.items():
  if n<MIN_CELL:continue
  out.append({"dimension":kind,"year":year,"label":name,"province":province or None,
    "report_rows":n,"reported_victims_sum":victims if missing_victims==0 else None,
    "reported_dollar_loss_sum":round(loss,2) if missing_loss==0 else None,
    "rows_without_loss":missing_loss,"rows_without_victims":missing_victims,
    "source":"CAFC official public reports; self-reported unverified",
    "geography_basis":"report_submitter_province_not_verified_incident_site"})
 out.sort(key=lambda x:(x["dimension"],x["year"],x["label"],x["province"] or ""))
 return out,tally

def stream_csv(url=SOURCE_URL,session=None):
 session=session or requests.Session()
 with session.get(url,headers={"User-Agent":"SignalNorthResearch/1.0 (https://github.com/khaled-agi/Signal-North)"},
                  timeout=(15,90),stream=True) as response:
  response.raise_for_status()
  with tempfile.TemporaryFile(mode="w+b") as tmp:
   size=0
   for chunk in response.iter_content(chunk_size=1024*1024):
    if not chunk:continue
    size+=len(chunk)
    if size>MAX_BYTES:raise ValueError("CAFC CSV exceeds maximum expected size")
    tmp.write(chunk)
   if size<100:raise ValueError("CAFC CSV download too small")
   tmp.seek(0)
   with io.TextIOWrapper(tmp,encoding="utf-8-sig",errors="replace",newline="") as reader:
    result=aggregate(reader)
 return result,size

def run():
 clock=now()
 old=read(STATUS,{})
 status={"status":"not_attempted","last_attempt_at":iso(clock),
   "source":SOURCE_LABEL,"dataset_url":SOURCE_PAGE,
   "dataset_end_date":EXPECTED_LAST_DATE,
   "last_success_at":old.get("last_success_at"),
   "methodology":"Official reported fraud intake, not adjudicated crime; aggregate Canada-only reports, suppress cells under 5; never publish individual report IDs or demographics",
 }
 if os.environ.get("CAFC_OFFLINE")=="1":
  status["status"]="offline_not_scanned"
 else:
  last=old.get("last_success_at")
  if last:
   try:
    dt=datetime.fromisoformat(last)
    if clock-dt<timedelta(days=REFRESH_DAYS):
     status.update({"status":"cached_recent_success","last_attempt_at":iso(clock)})
   except ValueError:pass
  if status["status"]=="not_attempted":
   try:
    (cells,tally),size=stream_csv()
    if tally["canada_rows"]<=0:raise ValueError("CAFC returned no Canadian report rows")
    save(OUT,{"updated_at":iso(clock),"source":SOURCE_LABEL,
      "dataset_url":SOURCE_PAGE,"download_url":SOURCE_URL,
      "dataset_coverage":"2021-01-01 through 2025-09-30 as published",
      "last_source_record_date":EXPECTED_LAST_DATE,
      "aggregation_scope":"Canada-only rows; no person-level records",
      "minimum_public_cell_size":MIN_CELL,"rows":cells,
      "methodology":"CAFC reported fraud allegations; not verified crime. Number of original report rows and reported loss field, not unique victim incidents or population rates. Rows with missing losses show null aggregate, not zero. Source data stops September 2025."})
    status.update({"status":"ok","last_success_at":iso(clock),"bytes_downloaded":size,
      "aggregated_cells":len(cells),**tally})
   except (ValueError,OSError,requests.RequestException,csv.Error) as exc:
    status.update({"status":"error","error_type":type(exc).__name__})
 save(STATUS,status)
 print(json.dumps({k:status.get(k) for k in ("status","aggregated_cells","canada_rows","last_success_at")}))
if __name__=="__main__":run()
