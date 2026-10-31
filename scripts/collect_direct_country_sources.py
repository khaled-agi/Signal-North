#!/usr/bin/env python3
"""Direct original-domain RSS/Atom discovery, independently from Google News.

Every source's actual endpoint is checked; errors and empty feeds are recorded.
Agency posts are publication leads, not adjudicated enforcement orders.
Market is the source's jurisdiction, not an alleged incident's location.
No content scraping, no social posts, no bypassing paywalls or restrictions.
"""
from __future__ import annotations
import hashlib,json,os,re,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit,urljoin
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
FEED=DATA/"direct_country_sources.json"
STATUS=DATA/"direct_country_source_status.json"
STATE=DATA/"direct_country_source_state.json"
CATALOG=DATA/"direct_country_source_catalog.json"
USER_AGENT="SignalNorthResearch/1.0 (+https://github.com/khaled-agi/Signal-North; direct public RSS metadata)"
ALLOW_KINDS={"newspaper","regulator","central_bank","police","fiu"}
SIGNAL=re.compile(r"fraud|scam|phish|launder|embezzl|ponzi|sanction|penalt|fined|forger|"
 r"money mule|crypto scam|cybercrime|identity theft|investment scheme|"
 r"estafa|estafas|fraude|escroquer|arnaque|blanchiment|burla|golpe|"
 r"诈骗|詐騙|洗钱|詐欺| धोखाधड़ी|धोखाधड़ी|"
 r"penipuan|lừa đảo|หลอกลวง|محتال|احتيال|نصب",re.I)
MAX_BYTES=1_200_000
MAX_ITEMS=40
MAX_DAYS=180
MAX_STORED=3500
BATCH=12
def now():return datetime.now(timezone.utc)
def stamp(t=None):return (t or now()).isoformat(timespec="seconds")
def read(path,default):
 try:return json.loads(path.read_text("utf-8"))
 except FileNotFoundError:return default
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n","utf-8")
def legal_link(url,domain):
 try:p=urlsplit(url)
 except ValueError:return None
 host=(p.hostname or "").lower()
 if (p.scheme!="https" or p.username or p.password or p.port not in (None,443)
     or not(host==domain or host.endswith("."+domain)) or len(url)>2048):return None
 return url
def parse_time(value):
 if not value:return None
 try:
  x=parsedate_to_datetime(value)
 except (TypeError,ValueError,IndexError):
  try:x=datetime.fromisoformat(value.replace("Z","+00:00"))
  except ValueError:return None
 if not x.tzinfo:x=x.replace(tzinfo=timezone.utc)
 return x.astimezone(timezone.utc)
def tag(el):return el.tag.rsplit("}",1)[-1]
def child(el,name):
 for x in el:
  if tag(x)==name:return x
 return None
def val(el,name):
 x=child(el,name)
 return " ".join("".join(x.itertext()).split()) if x is not None else ""
def items(payload,source,clock=None):
 """Strict original-domain RSS/Atom entries, with publication date and topic."""
 clock=clock or now()
 try:root=ET.fromstring(payload)
 except ET.ParseError:return []
 rows=[]
 domain=source["domain"]
 for entry in list(root.iter()):
  if tag(entry) not in ("item","entry"):continue
  title=val(entry,"title")[:300]
  if not title or not SIGNAL.search(title):continue
  url=val(entry,"link")
  if not url:
   for link in entry:
    if tag(link)=="link" and link.attrib.get("href"):
     if link.attrib.get("rel","alternate")=="alternate":
      url=link.attrib["href"];break
  url=urljoin(source["feed_url"],url)
  if not legal_link(url,domain):continue
  published=parse_time(val(entry,"pubDate") or val(entry,"published") or val(entry,"updated"))
  if not published or not(clock-timedelta(days=MAX_DAYS)<=published<=clock+timedelta(days=1)):continue
  key=hashlib.sha256((source["id"]+"|"+url.split("?",1)[0]).encode()).hexdigest()[:20]
  rows.append({"id":"direct-"+key,"country_code":source["country_code"],
   "source_id":source["id"],"source_name":source["name"],"source_kind":source["kind"],
   "title":title,"url":url,"published_at":stamp(published),
   "evidence_status":"direct_publisher_publication_unverified",
   "country_basis":"publisher_source_market_not_verified_incident_location",
   "geographic_note":"Source market or regulator jurisdiction, not a verified offence location",
   "is_official_source":source["kind"]!="newspaper",
   "review_status":"not_source_reviewed",
   "legal_status":"not_assessed_not_final_enforcement",
  })
 return sorted(rows,key=lambda x:x["published_at"],reverse=True)[:MAX_ITEMS]
def scan(source,clock=None):
 clock=clock or now()
 try:
  r=requests.get(source["feed_url"],headers={"User-Agent":USER_AGENT},timeout=20)
  r.raise_for_status()
  if len(r.content)>MAX_BYTES:raise ValueError("oversize feed")
  records=items(r.content,source,clock)
  # A working feed can produce zero fraud-relevant records. That's not "no news".
  return records,{"status":"ok" if records else "empty","accepted":len(records),
                  "checked_at":stamp(clock),"feed_http_status":r.status_code}
 except (requests.RequestException,ValueError) as e:
  return [],{"status":"error","accepted":0,"checked_at":stamp(clock),
             "error_type":type(e).__name__}
def catalog():
 sources=read(CATALOG,{"sources":[]})["sources"]
 ids=set()
 for s in sources:
  if s["id"] in ids:raise ValueError("duplicate source id")
  ids.add(s["id"])
  if s["kind"] not in ALLOW_KINDS:raise ValueError("unclassified source")
  if not legal_link(s["feed_url"],s["domain"]):raise ValueError("non-original-domain feed")
 return sources
def run():
 clock=now()
 sources=catalog()
 prior=read(STATUS,{"sources":{}}).get("sources",{})
 progress=read(STATE,{"next_cursor":0})
 existing=read(FEED,{"leads":[]}).get("leads",[])
 cursor=int(progress.get("next_cursor",0))%len(sources) if sources else 0
 count=min(len(sources),max(0,int(os.environ.get("DIRECT_SOURCE_BATCH",str(BATCH)))))
 selected=[sources[(cursor+i)%len(sources)] for i in range(count)] if sources else []
 if os.environ.get("DIRECT_SOURCE_OFFLINE")=="1":selected=[]
 sources_by_id={s["id"]:s for s in sources}
 cutoff=clock-timedelta(days=MAX_DAYS)
 retained={}
 for x in existing:
  source=sources_by_id.get(x.get("source_id"))
  if not source or not legal_link(x.get("url",""),source["domain"]):continue
  p=parse_time(x.get("published_at"))
  if p is not None and p>=cutoff:retained[x["id"]]=x
 health=dict(prior)
 with ThreadPoolExecutor(max_workers=4) as pool:
  jobs={pool.submit(scan,s,clock):s for s in selected}
  for f in as_completed(jobs):
   source=jobs[f];rows,state=f.result()
   health[source["id"]]={**state,"source_kind":source["kind"],
                         "country_code":source["country_code"],"name":source["name"]}
   for x in rows:retained[x["id"]]=x
 output=sorted(retained.values(),key=lambda x:x["published_at"],reverse=True)[:MAX_STORED]
 write(FEED,{"updated_at":stamp(clock),"leads":output,
  "methodology":"Direct original-domain RSS/Atom metadata. Source country does not imply incident geography. Regulators/police/FIUs yield publication leads, not confirmed final enforcement."})
 write(STATUS,{"updated_at":stamp(clock),"sources_configured":len(sources),
  "sources_attempted":sum(bool(h.get("checked_at")) for h in health.values()),
  "sources_with_results":sum(h.get("accepted",0)>0 for h in health.values()),
  "countries_configured":len(set(s["country_code"] for s in sources)),
  "stored_leads":len(output),"sources":health,
  "coverage_note":"Only verified URL configurations are targeted. No result never means no national news/enforcement."})
 write(STATE,{"next_cursor":(cursor+len(selected))%len(sources) if sources else 0})
 print(json.dumps({"sources_scanned":len(selected),"stored":len(output),
                   "configured":len(sources)}))
if __name__=="__main__":run()
