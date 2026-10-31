#!/usr/bin/env python3
"""Direct publisher/authority RSS and index monitoring alongside Google News.

Only original publisher-controlled URLs are indexed. Source country records
where the publisher/agency operates, never alleged incident locations.
Publications never become confirmed enforcement actions automatically.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

try:
 from .direct_source_catalogue import SOURCES
 from .world_country_lenses import CRIME_TERMS
except ImportError:
 from direct_source_catalogue import SOURCES
 from world_country_lenses import CRIME_TERMS

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUTPUT=DATA/"world_direct_sources.json"
STATUS=DATA/"world_direct_source_status.json"
STATE=DATA/"world_direct_source_state.json"
UA={"User-Agent":"SignalNorthResearch/1.0 (+https://github.com/khaled-agi/Signal-North; original-source citations only)"}
MAX_AGE_DAYS=180
MAX_PER_SOURCE=65
MAX_ALL=1700
BATCH=12
DATE_PATTERN=re.compile(r"\b((?:20)\d\d[-/]\d\d?[-/]\d\d?|\d\d?[\s/-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/-]20\d\d)\b",re.I)
# Keywords describe *possible source relevance*, never guilt or final legal status.
TERM=re.compile(
 r"fraud|scam|phish|launder|suspicious transaction|securit(?:y|ies) violation|"
 r"enforcement|penalt|sanction|settlement|market manipul|money mule|"
 r"prohibition order|warning against|unlicensed|identity theft|"
 r"financial crime|financial intelligence|embezzl|forger|"
 r"securities order|financial misconduct|money laundering|fraudster|"
 r"escroquer|arnaque|fraude|estafa|estafas|burla|golpe|"
 r"mashtrim|penipuan|pencucian uang|dugaan tindak pidana|"
 r"诈骗|詐騙|造假|洗钱|洗錢|处罚|處罰|罚款|罰款|行政处罚|违法违规|"
 r"احتيال|نصب|غسل الأموال| धोखाधड़ी|ठगी|"
 r"မလိမ်|လိမ်လည်|mōsadi| மோசடி|"
 r"បោកប្រាស់|หลอกลวง|ฟอกเงิน|lừa đảo|rửa tiền|"
 r"uadilifu|ulaghai|zamba|svindel",re.I)
# Better relevance for official FMA 'public warning' etc; general policy
# or macroeconomic bulletins without crime terms should not enter the feed.
IGNORE=re.compile(r"careers|job opening|contact us|cookie|privacy policy|"
                  r"annual report|monetary policy statement|exchange rates|"
                  r"terms of use|investor education seminar",re.I)

def utcnow():return datetime.now(timezone.utc)
def iso(d):return d.isoformat(timespec="seconds")
def load(path,default):
 try:return json.loads(path.read_text("utf-8"))
 except (OSError,ValueError):return default
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n","utf-8")
def valid_original(url,source):
 if not isinstance(url,str):return None
 url=url.strip()
 if len(url)>2200:return None
 try:u=urlsplit(url)
 except ValueError:return None
 expected=source["domain"].lower()
 host=(u.hostname or "").lower()
 if (u.scheme!="https" or u.username or u.password or
     u.port not in (None,443) or
     not (host==expected or host.endswith("."+expected))):return None
 if not u.path or u.path=="/":return None
 return url

def parse_date(raw):
 if not raw:return None
 try:
  v=parsedate_to_datetime(str(raw))
  if v.tzinfo is None:v=v.replace(tzinfo=timezone.utc)
  return iso(v.astimezone(timezone.utc))
 except (TypeError,ValueError,OverflowError,IndexError):pass
 try:
  from dateutil.parser import parse
  val=parse(str(raw),fuzzy=False,dayfirst=False)
  if val.tzinfo is None:val=val.replace(tzinfo=timezone.utc)
  return iso(val.astimezone(timezone.utc))
 except (ValueError,TypeError,OverflowError):return None

def relevant(title):
 clean=" ".join(str(title or "").split())[:320]
 return bool(len(clean)>=16 and not IGNORE.search(clean) and TERM.search(clean))

def make_record(title,url,source,observed_at,published_at=None):
 if not relevant(title):return None
 original=valid_original(url,source)
 if original is None:return None
 if published_at:
  try:
   published=datetime.fromisoformat(published_at)
   if published>observed_at+timedelta(days=2) or published<observed_at-timedelta(days=MAX_AGE_DAYS):return None
  except ValueError:published_at=None
 key=hashlib.sha256((source["id"]+"|"+original.split("?")[0]).encode("utf-8")).hexdigest()[:22]
 return {
  "id":"direct-"+key,"title":" ".join(title.split())[:320],
  "url":original,"source_name":source["name"],"source_id":source["id"],
  "source_type":source["kind"],"source_domain":source["domain"],
  "publisher_country_code":source["country"],
  "country_code":None,"country_basis":"publisher_or_agency_home_jurisdiction_not_event_location",
  "published_at":published_at,"first_seen_at":iso(observed_at),
  "date_basis":"source_feed_publication_date" if published_at else "first_indexed_not_publication_date",
  "evidence_status":"original_publisher_publication_unreviewed",
  "verified_final_enforcement":False,
  "geographic_note":"Publisher or regulator jurisdiction, NOT the alleged offence location",
  "source_kind":"direct_original_website",
 }

def parse_rss(raw,source,ts):
 if len(raw)>3_000_000:raise ValueError("large RSS")
 root=ET.fromstring(raw)
 found=[]
 for el in root.findall(".//item")+root.findall(".//{*}entry"):
  def val(tag):
   node=el.find(tag)
   if node is None:node=el.find("{*}"+tag)
   return (node.text or "").strip() if node is not None else ""
  title=val("title")
  link=val("link")
  if not link:
   for ln in el.findall("{*}link"):
    if ln.get("href") and ln.get("rel","alternate")=="alternate":
     link=ln.get("href");break
  if not link:continue
  date=parse_date(val("pubDate") or val("published") or val("updated") or val("date"))
  record=make_record(title,link,source,ts,date)
  if record:found.append(record)
 return found

def parse_index(raw,source,ts):
 if len(raw)>3_000_000:raise ValueError("large HTML")
 soup=BeautifulSoup(raw,"html.parser")
 found=[]
 seen=set()
 for anchor in soup.select("a[href]"):
  href=anchor.get("href","")
  url=valid_original(urljoin(source["url"],href),source)
  if not url or url in seen:continue
  if source.get("path_hint") and source["path_hint"] not in urlsplit(url).path:continue
  title=anchor.get_text(" ",strip=True)
  if len(title)<16:
   parent=anchor.find_parent(["article","li","h2","h3"])
   if parent:title=parent.get_text(" ",strip=True)[:300]
  if not relevant(title):continue
  seen.add(url)
  # Do NOT guess dates from navigation/list item context. If no clearly
  # machine-readable date is attached to the anchor, use first-indexed only.
  record=make_record(title,url,source,ts)
  if record:found.append(record)
  if len(found)>=85:break
 return found

def fetch_source(source,ts):
 try:
  resp=requests.get(source["url"],headers=UA,timeout=20,allow_redirects=True)
  resp.raise_for_status()
  final=urlsplit(resp.url)
  host=(final.hostname or "").lower()
  expected=source["domain"].lower()
  if (final.scheme!="https" or not (host==expected or host.endswith("."+expected))):
   raise ValueError("source redirected outside original publisher domain")
  if len(resp.content)>3_000_000:raise ValueError("source response exceeds size limit")
  ctype=resp.headers.get("content-type","").lower()
  if source["format"]=="rss":
   if not any(m in ctype for m in ("xml","rss","text/plain","application/octet-stream")):
    raise ValueError("RSS response is not XML")
   found=parse_rss(resp.content,source,ts)
  else:
   if not any(m in ctype for m in ("html","text/plain")):
    raise ValueError("index response is not HTML")
   found=parse_index(resp.content,source,ts)
  return found,{"status":"reporting_found" if found else "empty_no_matching_titles",
                "checked_at":iso(ts),"accepted":len(found),
                "fetch_type":source["format"],"error_type":None}
 except (requests.RequestException,ET.ParseError,ValueError) as exc:
  return [],{"status":"error","checked_at":iso(ts),"accepted":0,
              "fetch_type":source["format"],"error_type":type(exc).__name__}

def retained(records,ts):
 cutoff=ts-timedelta(days=MAX_AGE_DAYS)
 sources={x["id"]:x for x in SOURCES}
 grouped={}
 for rec in records:
  source=sources.get(rec.get("source_id"))
  if not source or valid_original(rec.get("url"),source) is None:continue
  if rec.get("evidence_status")!="original_publisher_publication_unreviewed":continue
  try:
   date=datetime.fromisoformat(rec.get("first_seen_at") or "")
   if date.tzinfo is None:continue
  except (ValueError,TypeError):continue
  if date<cutoff or date>ts+timedelta(days=2):continue
  grouped.setdefault(source["id"],{})[rec["id"]]=rec
 rows=[]
 for items in grouped.values():
  rows.extend(sorted(items.values(),key=lambda r:r["published_at"] or r["first_seen_at"],
     reverse=True)[:MAX_PER_SOURCE])
 return sorted(rows,key=lambda r:r["published_at"] or r["first_seen_at"],
               reverse=True)[:MAX_ALL]

def run():
 ts=utcnow();previous=load(OUTPUT,{"records":[]});old=load(STATUS,{"sources":{}})
 state=load(STATE,{"next_cursor":0})
 cursor=int(state.get("next_cursor",0))%len(SOURCES)
 batch=max(1,min(len(SOURCES),int(os.getenv("DIRECT_SOURCE_BATCH",str(BATCH)))))
 selected=[SOURCES[(cursor+i)%len(SOURCES)] for i in range(batch)]
 if os.getenv("DIRECT_SOURCE_OFFLINE")=="1":selected=[]
 known={r["id"]:r for r in retained(previous.get("records",[]),ts)}
 health={
  src["id"]:{**old.get("source_health",{}).get(src["id"],{}),
       "country_code":src["country"],"name":src["name"],
       "source_type":src["kind"],"source_url":src["url"],
       "status":old.get("source_health",{}).get(src["id"],{}).get("status","not_attempted")}
  for src in SOURCES
 }
 with ThreadPoolExecutor(max_workers=5) as pool:
  jobs={pool.submit(fetch_source,src,ts):src for src in selected}
  for fut in as_completed(jobs):
   src=jobs[fut];rows,stats=fut.result()
   health[src["id"]]={**stats,"country_code":src["country"],"name":src["name"],
                       "source_type":src["kind"],"source_url":src["url"]}
   for item in rows:
    if item["id"] in known:
     item["first_seen_at"]=known[item["id"]]["first_seen_at"]
    known[item["id"]]=item
 records=retained(known.values(),ts)
 attempted={s["country_code"] for s in health.values() if s.get("checked_at")}
 success={s["country_code"] for s in health.values() if s.get("status")!="error" and s.get("checked_at")}
 save(OUTPUT,{"updated_at":iso(ts),"records":records,
   "methodology":"Direct original-site RSS/index headlines only. Publisher/agency jurisdiction is NOT an alleged incident location; a regulator publication is NOT automatically a confirmed final enforcement order. RSS publication dates when supplied; HTML indexes without dates use first indexed."})
 save(STATUS,{"last_completed_at":iso(ts),"configured_sources":len(SOURCES),
   "configured_countries":len({s["country"] for s in SOURCES}),
   "countries_attempted":len(attempted),"countries_with_successful_fetches":len(success),
   "source_attempts":sum(bool(s.get("checked_at")) for s in health.values()),
   "sources_successful_last_attempt":sum(bool(s.get("checked_at")) and s.get("status")!="error" for s in health.values()),
   "records_retained":len(records),"source_health":health,
   "warning":"Unconfigured market != no news. Empty source != no financial crime. Publishers' countries and content locations are distinct."})
 save(STATE,{"next_cursor":(cursor+len(selected))%len(SOURCES) if selected else cursor})
 print(json.dumps({"sources_configured":len(SOURCES),"sources_scanned":len(selected),"records":len(records),
                   "countries_with_live_sources":len(success)}))

if __name__=="__main__":run()
