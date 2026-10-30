#!/usr/bin/env python3
"""Official-domain enforcement DISCOVERY across national regulators.

GDELT indexes publicly reported pages. This collector requires the ORIGINAL
URL to belong to the nominated government/regulator domain. It publishes
official-site PUBLICATION LEADS only: listing presence is not legal status,
a final penalty, or confirmation of allegations. No articles/scraped bodies.
Never conflate a GDELT first-seen date with an agency publication/action date.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUTPUT=DATA/"global_regulator_publications.json"
STATUS=DATA/"global_regulator_publications_status.json"
STATE=DATA/"global_regulator_publications_state.json"
ENDPOINT="https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS={"User-Agent":"SignalNorthResearch/1.0 (official regulatory publication discovery; https://github.com/khaled-agi/Signal-North)"}
# Explicit agency-domain bindings. Expand only after reviewing real agency sites.
# These are discovery targets, NOT claims of full official action collection.
REGULATORS=[
 ("SG","Singapore","MAS","mas.gov.sg"),
 ("NZ","New Zealand","FMA","fma.govt.nz"),
 ("CH","Switzerland","FINMA","finma.ch"),
 ("AU","Australia","AUSTRAC","austrac.gov.au"),
 ("IE","Ireland","Central Bank of Ireland","centralbank.ie"),
 ("HK","Hong Kong","HKMA","hkma.gov.hk"),
 ("FR","France","AMF","amf-france.org"),
 ("DE","Germany","BaFin","bafin.de"),
 ("IN","India","SEBI","sebi.gov.in"),
 ("IN","India","RBI","rbi.org.in"),
 ("JP","Japan","FSA","fsa.go.jp"),
 ("ZA","South Africa","FSCA","fsca.co.za"),
 ("ZA","South Africa","FIC","fic.gov.za"),
 ("NG","Nigeria","EFCC","efcc.gov.ng"),
 ("KE","Kenya","Central Bank of Kenya","centralbank.go.ke"),
 ("AE","United Arab Emirates","Central Bank of UAE","centralbank.ae"),
 ("GB","United Kingdom","FCA","fca.org.uk"),
 ("US","United States","CFTC","cftc.gov"),
 ("US","United States","SEC","sec.gov"),
 ("US","United States","Federal Reserve","federalreserve.gov"),
 ("US","United States","CFPB","consumerfinance.gov"),
 ("US","United States","OFAC","ofac.treasury.gov"),
 ("BR","Brazil","Banco Central do Brasil","bcb.gov.br"),
 ("BR","Brazil","CVM","gov.br"),
 ("ES","Spain","CNMV","cnmv.es"),
 ("NO","Norway","Finanstilsynet","finanstilsynet.no"),
 ("NL","Netherlands","AFM","afm.nl"),
 ("BE","Belgium","FSMA","fsma.be"),
 ("KR","South Korea","FSC","fsc.go.kr"),
 ("CA","Canada","FINTRAC","fintrac-canafe.canada.ca"),
]
# Only data with positive title evidence is accepted; don't place generic
# consultations / annual reports into an enforcement decisions feed.
ACTIONS=re.compile(
 r"\b(enforcement|penalt(?:y|ies)|fined?|sanction|prohibition order|revok(?:ed|es|ation)|"
 r"fraud (?:charges|conviction|action)|settlement|cease and desist|"
 r"administrative order|disciplin(?:ary|e)|multa|sanci[oó]n|amende|"
 r"geldbu(?:ße|sse)|bu(?:ß|ss)geld|abus de march[eé]|处罚|罚款)\b",re.I
)
EXCLUDED=re.compile(r"\b(job opening|career|annual report|consultation paper|"
                    r"enforcement policy|our approach to enforcement|newsletter|"
                    r"fraud warning (?:tips|guide)|how to avoid scams)\b",re.I)
MAX_DAYS=180
MAX_PER_AGENCY=120
MAX_ALL=4000
BATCH=6

def stamp():return datetime.now(timezone.utc).isoformat(timespec="seconds")

def read(path,default):
 try:return json.loads(path.read_text("utf-8"))
 except FileNotFoundError:return default

def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n","utf-8")

def original_official_link(url,domain):
 if not isinstance(url,str):return None
 u=urlsplit(url)
 host=(u.hostname or "").lower()
 if (u.scheme!="https" or u.username or u.password or u.port not in (None,443)
     or not (host==domain or host.endswith("."+domain))
     or len(url)>2048):
  return None
 # e.g. gov.br is a government platform that hosts unrelated agencies:
 # ONLY keep Brazilian securities commission CVM URL paths.
 if domain=="gov.br" and "/cvm/" not in u.path.lower():
  return None
 if not u.path or u.path=="/":return None
 return url

def seendate(raw):
 try:
  dt=datetime.strptime(str(raw)[:14],"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
  if dt>datetime.now(timezone.utc)+timedelta(days=1):return None
  return dt.isoformat(timespec="seconds")
 except (ValueError,TypeError):return None

def parse_results(payload,agency,now=None):
 country,name,regulator,domain=agency
 now=now or datetime.now(timezone.utc)
 articles=payload.get("articles") or []
 rows=[]
 for article in articles:
  title=" ".join(str(article.get("title") or "").split())[:310]
  if not ACTIONS.search(title) or EXCLUDED.search(title):
   continue
  url=original_official_link(article.get("url"),domain)
  observed=seendate(article.get("seendate"))
  if not url or not observed or datetime.fromisoformat(observed)<now-timedelta(days=MAX_DAYS):
   continue
  key=hashlib.sha256((country+"|"+regulator+"|"+url.split("?")[0]).encode()).hexdigest()[:20]
  rows.append({
   "id":"regulator-lead-"+key,"country_code":country,"country":name,
   "regulator":regulator,"title":title,"source_url":url,
   "first_observed_at":observed,"published_at":None,
   "date_basis":"gdelt_first_seen_not_official_publication_date",
   "source_domain":domain,"source_kind":"original_regulator_website_publication",
   "evidence_tier":"official_site_publication_lead",
   "review_status":"legal_status_and_action_type_not_independently_checked",
   "status":"Agency-site announcement discovered. Check notice for legal status, appeals and relevance.",
   "category":"Possible enforcement / regulatory action",
   "location_role":"regulator_jurisdiction_country_center",
   "geographic_note":"Regulator jurisdiction; NOT incident location.",
   "discovery_method":"gdelt_doc_artlist_domain_restricted",
   "institution":None,"penalty_amount":None,"penalty_currency":None,
  })
 return rows

def query_url_params(agency):
 domain=agency[3]
 # Keep tight domain restriction in search, validate again on ALL returned URLs.
 return {
  "query":f'domain:{domain} (fine OR fined OR penalty OR sanctions OR enforcement OR "prohibition order" OR settlement)',
  "mode":"ArtList","format":"json","timespan":"3months","maxrecords":"100",
  "sort":"datedesc",
 }

def collect_one(agency):
 try:
  response=requests.get(ENDPOINT,params=query_url_params(agency),timeout=35,headers=HEADERS)
  response.raise_for_status()
  if len(response.content)>2_500_000:raise ValueError("response too large")
  payload=response.json()
  if not isinstance(payload,dict) or not isinstance(payload.get("articles",[]),list):
   raise ValueError("unexpected response structure")
  found=parse_results(payload,agency)
  return found,{"status":"ok" if found else "empty","accepted":len(found),
                "checked_at":stamp(),"source_domain":agency[3]}
 except (requests.RequestException,ValueError,KeyError) as exc:
  return [],{"status":"error","error_type":type(exc).__name__,
             "checked_at":stamp(),"source_domain":agency[3]}

def retain(items):
 cutoff=datetime.now(timezone.utc)-timedelta(days=MAX_DAYS)
 known={x[0]+":"+x[2]:x for x in REGULATORS}
 by_agency={}
 for item in items:
  key=str(item.get("country_code"))+":"+str(item.get("regulator"))
  source=known.get(key)
  if not source or original_official_link(item.get("source_url"),source[3]) is None:continue
  try:dt=datetime.fromisoformat(str(item.get("first_observed_at")))
  except ValueError:continue
  if dt<cutoff:continue
  if item.get("evidence_tier")!="official_site_publication_lead":continue
  by_agency.setdefault(key,{})[item["id"]]=item
 results=[r for values in by_agency.values() for r in sorted(values.values(),
          key=lambda x:x["first_observed_at"],reverse=True)[:MAX_PER_AGENCY]]
 return sorted(results,key=lambda x:x["first_observed_at"],reverse=True)[:MAX_ALL]

def run():
 DATA.mkdir(exist_ok=True,parents=True)
 existing=read(OUTPUT,{"leads":[]}).get("leads",[])
 prior=read(STATUS,{"agencies":{}}).get("agencies",{})
 progress=read(STATE,{"next_cursor":0})
 cursor=int(progress.get("next_cursor",0))%len(REGULATORS)
 size=min(len(REGULATORS),max(1,int(os.getenv("REGULATOR_SCAN_BATCH",str(BATCH)))))
 chosen=[REGULATORS[(cursor+i)%len(REGULATORS)] for i in range(size)]
 if os.getenv("REGULATOR_SCAN_OFFLINE")=="1":
  chosen=[]
 merged={r["id"]:r for r in retain(existing)}
 stats=dict(prior)
 with ThreadPoolExecutor(max_workers=3) as executor:
  jobs={executor.submit(collect_one,agency):agency for agency in chosen}
  for f in as_completed(jobs):
   agency=jobs[f];key=agency[0]+":"+agency[2]
   rows,health=f.result()
   stats[key]={**health,"country_code":agency[0],"regulator":agency[2]}
   for row in rows:
    old=merged.get(row["id"])
    if old:row["first_observed_at"]=min(row["first_observed_at"],old["first_observed_at"])
    merged[row["id"]]=row
 next_cursor=(cursor+len(chosen))%len(REGULATORS)
 records=retain(merged.values())
 write(OUTPUT,{"updated_at":stamp(),"leads":records,
  "methodology":"Official-domain links identified by GDELT. Publication leads, NOT verified final enforcement actions. Date is first GDELT observation, not legal action/publication date."})
 write(STATUS,{"last_completed_at":stamp(),"regulators_configured":len(REGULATORS),
   "regulators_attempted":sum(bool(x.get("checked_at")) for x in stats.values()),
   "countries_with_publication_leads":len({x["country_code"] for x in records}),
   "leads_count":len(records),"agencies":stats,
   "coverage_note":"Configured agencies are a small subset of world regulators, not comprehensive enforcement. Official-domain publication leads require individual legal status confirmation."})
 write(STATE,{"next_cursor":next_cursor})
 print(json.dumps({"configured":len(REGULATORS),"scanned":len(chosen),
                   "leads":len(records),"countries_with_leads":len({x["country_code"] for x in records})}))

if __name__=="__main__":run()
