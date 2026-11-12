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

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUTPUT=DATA/"global_regulator_publications.json"
STATUS=DATA/"global_regulator_publications_status.json"
STATE=DATA/"global_regulator_publications_state.json"
ENDPOINT="https://api.gdeltproject.org/api/v2/doc/doc"
NEWS_INDEX="https://news.google.com/rss/search"
# GDELT allows roughly one request per 5 seconds and throttles shared CI IPs.
GDELT_SPACING=float(os.getenv("GDELT_SPACING_SECONDS","6"))
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
 r"\b(enforcement|penalt(?:y|ies)|penali[sz](?:ed|es)|fine[sd]?|sanction(?:s|ed)?|"
 r"prohibition orders?|revok(?:ed|es|ation)|censure[sd]?|banned|bans|market abuse|"
 r"warning notice|final notice|charged|convicted|"
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

def news_index_url(agency):
 domain=agency[3]
 terms="(fine OR fined OR penalty OR sanction OR enforcement OR settlement OR prohibition)"
 site=domain if domain!="gov.br" else "gov.br/cvm"
 return NEWS_INDEX+"?"+urlencode({"q":f"site:{site} {terms} when:90d","hl":"en-US","gl":"US","ceid":"US:en"})

def parse_news_index(raw,agency,now=None):
 """Google News RSS fallback. Item links are news.google.com redirects, so the
 regulator domain is verified from the RSS <source url=...> attribute instead
 and the lead is labelled with a distinct, weaker evidence tier."""
 country,name,regulator,domain=agency
 now=now or datetime.now(timezone.utc)
 root=ET.fromstring(raw)
 rows=[]
 for item in root.findall(".//channel/item")[:100]:
  title=" ".join((item.findtext("title") or "").split())[:310]
  src=item.find("source")
  src_url=(src.get("url") if src is not None else "") or ""
  publisher=" ".join(((src.text if src is not None else "") or "").split())[:120]
  # Google appends " - Publisher" to titles; drop it before matching.
  if publisher and title.endswith(" - "+publisher):title=title[:-(len(publisher)+3)].strip()
  link=str(item.findtext("link") or "").strip()
  host=(urlsplit(src_url).hostname or "").lower()
  if not (host==domain or host.endswith("."+domain)) or urlsplit(src_url).scheme!="https":continue
  if not link.startswith("https://") or len(link)>2048:continue
  if not ACTIONS.search(title) or EXCLUDED.search(title):continue
  try:
   pub=parsedate_to_datetime(item.findtext("pubDate"))
   if pub.tzinfo is None:pub=pub.replace(tzinfo=timezone.utc)
  except (TypeError,ValueError,IndexError,OverflowError):continue
  if pub<now-timedelta(days=MAX_DAYS) or pub>now+timedelta(days=1):continue
  key=hashlib.sha256((country+"|"+regulator+"|"+title.casefold()).encode()).hexdigest()[:20]
  rows.append({
   "id":"regulator-lead-"+key,"country_code":country,"country":name,
   "regulator":regulator,"title":title,"source_url":link,
   "verified_source_domain":host,
   "first_observed_at":pub.astimezone(timezone.utc).isoformat(timespec="seconds"),
   "published_at":None,
   "date_basis":"news_index_publication_date_not_official_action_date",
   "source_domain":domain,"source_kind":"regulator_website_publication_via_news_index",
   "evidence_tier":"official_domain_publication_lead_via_news_index",
   "review_status":"legal_status_and_action_type_not_independently_checked",
   "status":"Agency-site announcement indexed by Google News. Open the notice to confirm legal status.",
   "category":"Possible enforcement / regulatory action",
   "location_role":"regulator_jurisdiction_country_center",
   "geographic_note":"Regulator jurisdiction; NOT incident location.",
   "discovery_method":"google_news_rss_site_restricted",
   "institution":None,"penalty_amount":None,"penalty_currency":None,
  })
 return rows

class RateLimited(Exception):
 pass

def fetch_gdelt(session,agency):
 for attempt in range(2):
  response=session.get(ENDPOINT,params=query_url_params(agency),timeout=35,headers=HEADERS)
  if response.status_code==429:
   if attempt==0:
    time.sleep(max(GDELT_SPACING*2,10));continue
   raise RateLimited("GDELT HTTP 429")
  response.raise_for_status()
  if len(response.content)>2_500_000:raise ValueError("response too large")
  # GDELT answers malformed or throttled queries with a plain-text notice.
  if "json" not in response.headers.get("Content-Type","") and not response.text.lstrip().startswith("{"):
   raise ValueError("GDELT returned non-JSON: "+response.text[:80])
  payload=response.json()
  if not isinstance(payload,dict) or not isinstance(payload.get("articles",[]),list):
   raise ValueError("unexpected response structure")
  return parse_results(payload,agency)
 raise RateLimited("GDELT HTTP 429")

def fetch_news_index(session,agency):
 response=session.get(news_index_url(agency),timeout=30,headers={"User-Agent":"Mozilla/5.0 (compatible; SignalNorthResearch/1.0)"})
 response.raise_for_status()
 return parse_news_index(response.content,agency)

def collect_one(agency,session=None,use_gdelt=True):
 session=session or requests.Session()
 found=[];methods={};errors={}
 if use_gdelt:
  try:
   rows=fetch_gdelt(session,agency);found+=rows;methods["gdelt"]=len(rows)
  except RateLimited as exc:
   errors["gdelt"]="rate_limited"
  except (requests.RequestException,ValueError,KeyError) as exc:
   errors["gdelt"]=type(exc).__name__
 else:
  errors["gdelt"]="skipped_after_rate_limit"
 try:
  rows=fetch_news_index(session,agency);found+=rows;methods["news_index"]=len(rows)
 except (requests.RequestException,ValueError,ET.ParseError) as exc:
  errors["news_index"]=type(exc).__name__
 status="ok" if found else ("empty" if methods else "error")
 health={"status":status,"accepted":len(found),"checked_at":stamp(),
         "source_domain":agency[3],"methods":methods}
 if errors:health["errors"]=errors
 if status=="error":health["error_type"]=";".join(f"{k}:{v}" for k,v in errors.items())
 return found,health

def retain(items):
 cutoff=datetime.now(timezone.utc)-timedelta(days=MAX_DAYS)
 known={x[0]+":"+x[2]:x for x in REGULATORS}
 by_agency={}
 for item in items:
  key=str(item.get("country_code"))+":"+str(item.get("regulator"))
  source=known.get(key)
  if not source:continue
  tier=item.get("evidence_tier")
  if tier=="official_site_publication_lead":
   if original_official_link(item.get("source_url"),source[3]) is None:continue
  elif tier=="official_domain_publication_lead_via_news_index":
   host=str(item.get("verified_source_domain") or "")
   if not (host==source[3] or host.endswith("."+source[3])):continue
   if not str(item.get("source_url") or "").startswith("https://"):continue
  else:continue
  try:dt=datetime.fromisoformat(str(item.get("first_observed_at")))
  except ValueError:continue
  if dt<cutoff:continue
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
 session=requests.Session()
 gdelt_ok=True
 for index,agency in enumerate(chosen):
  key=agency[0]+":"+agency[2]
  rows,health=collect_one(agency,session,use_gdelt=gdelt_ok)
  if health.get("errors",{}).get("gdelt")=="rate_limited":gdelt_ok=False
  previous=prior.get(key,{})
  if health["status"]=="error" and previous.get("last_success_at"):
   health["status"]="failed_last_good_preserved"
  if health["status"] in ("ok","empty"):health["last_success_at"]=health["checked_at"]
  elif previous.get("last_success_at"):health["last_success_at"]=previous["last_success_at"]
  stats[key]={**health,"country_code":agency[0],"regulator":agency[2]}
  for row in rows:
   old=merged.get(row["id"])
   if old:row["first_observed_at"]=min(row["first_observed_at"],old["first_observed_at"])
   merged[row["id"]]=row
  if index<len(chosen)-1:time.sleep(GDELT_SPACING if gdelt_ok else 1.0)
 next_cursor=(cursor+len(chosen))%len(REGULATORS)
 records=retain(merged.values())
 write(OUTPUT,{"updated_at":stamp(),"leads":records,
  "methodology":"Official-domain publications discovered via GDELT (original agency URL) or Google News site search (agency domain verified from the RSS source attribute; link is a news-index redirect). Publication leads, NOT verified final enforcement actions. Dates are discovery/index dates, not legal action dates."})
 write(STATUS,{"last_completed_at":stamp(),"regulators_configured":len(REGULATORS),
   "regulators_attempted":sum(bool(x.get("checked_at")) for x in stats.values()),
   "regulators_with_recent_success":sum(bool(x.get("last_success_at")) for x in stats.values()),
   "countries_with_publication_leads":len({x["country_code"] for x in records}),
   "leads_count":len(records),"agencies":stats,
   "coverage_note":"Configured agencies are a small subset of world regulators, not comprehensive enforcement. Official-domain publication leads require individual legal status confirmation."})
 write(STATE,{"next_cursor":next_cursor})
 print(json.dumps({"configured":len(REGULATORS),"scanned":len(chosen),
                   "leads":len(records),"countries_with_leads":len({x["country_code"] for x in records})}))

if __name__=="__main__":run()
