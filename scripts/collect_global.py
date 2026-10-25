#!/usr/bin/env python3
"""Global official enforcement discovery, starting with USA and UK regulators.

Only index actual published regulator entries and original links. AUSTRAC
decisions are currently represented by source-verified seed records; no scraping
claims are made for unavailable feeds. Keep original penalty currencies.
"""
from __future__ import annotations
import hashlib,json,re,os
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup
from requests import Session
from requests.exceptions import RequestException

DATA=Path(__file__).resolve().parents[1]/"data"
SEED=DATA/"global_enforcement_seed.json"
OUTPUT=DATA/"global_enforcement.json"
STATUS=DATA/"global_source_status.json"
HEADERS={"User-Agent":"SignalNorthResearch/0.7 (public enforcement metadata only; https://github.com/khaled-agi/Signal-North)","Accept":"text/html,*/*"}
SOURCES=[
 ("FinCEN", "US","United States","https://www.fincen.gov/news/enforcement-actions"),
 ("FCA","GB","United Kingdom","https://www.fca.org.uk/news/news-stories/2026-fines"),
 ("AUSTRAC","AU","Australia","https://www.austrac.gov.au/about-us/record-our-actions/enforcement-actions-taken"),
]
BASE_CENTERS={"US":(39.8,-98.6),"GB":(54,-2.7),"AU":(-25,134),"HK":(22.4,114.1),"SG":(1.35,103.8),"IE":(53.3,-8)}
def now():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def date_us(raw):
 try:return datetime.strptime(raw.strip(),"%m/%d/%Y").strftime("%Y-%m-%d")
 except ValueError:return None
def date_uk(raw):
 try:return datetime.strptime(raw.strip(),"%d/%m/%Y").strftime("%Y-%m-%d")
 except ValueError:return None
def valid_url(url,expected):
 parsed=urlparse(url)
 return parsed.scheme=="https" and (parsed.hostname==expected or parsed.hostname.endswith("."+expected))
def valid(item):
 return (item.get("country_code") in BASE_CENTERS and
         item.get("source_url","").startswith("https://") and
         bool(item.get("published_at")) and bool(item.get("title")))
def scan_fincen(session):
 url=SOURCES[0][3];r=session.get(url,timeout=38);r.raise_for_status()
 soup=BeautifulSoup(r.text,"html.parser");rows=[]
 for tr in soup.select("tr"):
  cells=tr.find_all("td")
  if len(cells)<3:continue
  name=cells[0].get_text(" ",strip=True)
  day=date_us(cells[1].get_text(" ",strip=True))
  if not day or len(name)<12:continue
  anchor=cells[0].find("a",href=True)
  ref=urljoin(url,anchor["href"]) if anchor else url
  if not valid_url(ref,"fincen.gov"):continue
  matter=cells[2].get_text(" ",strip=True)
  sector=cells[3].get_text(" ",strip=True) if len(cells)>3 else "BSA/AML"
  if int(day[:4])<2020:continue
  rows.append({
   "id":"us-fincen-index-"+hashlib.sha256((day+"|"+matter+"|"+name).encode()).hexdigest()[:16],
   "country_code":"US","country":"United States","regulator":"FinCEN",
   "published_at":day,"institution":name.replace("In the Matter of ","").strip(),
   "title":name,"status":"official enforcement index entry; open notice for decision details",
   "category":"AML / BSA compliance · "+sector,
   "penalty_amount":None,"penalty_currency":"USD","source_url":ref,
   "location_role":"regulator_jurisdiction_country_center",
   "evidence_tier":"official_enforcement_index",
   "geographic_note":"US FinCEN jurisdiction, not location of alleged misconduct",
  })
 return rows
def scan_fca(session):
 all_rows=[]
 for year in range(2023,2027):
  url=f"https://www.fca.org.uk/news/news-stories/{year}-fines"
  r=session.get(url,timeout=35)
  r.raise_for_status()
  soup=BeautifulSoup(r.text,"html.parser")
  for tr in soup.select("tr"):
   cells=tr.find_all("td")
   if len(cells)<4:continue
   name=cells[0].get_text(" ",strip=True)
   day=date_uk(cells[1].get_text(" ",strip=True))
   if not day or not name:continue
   amount_text=cells[2].get_text(" ",strip=True)
   # Preserve GBP and avoid double counting: summary rows lack day/name.
   digits=re.sub(r"[^\d.]","",amount_text.replace(",",""))
   amount=float(digits) if digits and "£" in amount_text else None
   reason=cells[3].get_text(" ",strip=True)[:340]
   anchor=cells[3].find("a",href=True) or cells[0].find("a",href=True)
   detail=urljoin(url,anchor.get("href","")) if anchor else url
   if not valid_url(detail,"fca.org.uk"):continue
   all_rows.append({
    "id":"gb-fca-"+hashlib.sha256((name+"|"+day).encode()).hexdigest()[:16],
    "country_code":"GB","country":"United Kingdom","regulator":"FCA",
    "published_at":day,"institution":name,"title":"FCA fine: "+name,
    "status":"FCA published fine; legal grounds and appeal status require reading linked notice",
    "category":"Financial services enforcement","penalty_amount":amount,
    "penalty_currency":"GBP","source_url":detail,
    "location_role":"regulator_jurisdiction_country_center",
    "evidence_tier":"official_enforcement_index",
    "summary":reason,
    "geographic_note":"UK FCA jurisdiction, not fraud location",
   })
 return all_rows
def run():
 DATA.mkdir(parents=True,exist_ok=True)
 seed=json.loads(SEED.read_text("utf-8")).get("events",[])
 try:previous=json.loads(OUTPUT.read_text("utf-8")).get("events",[]) if OUTPUT.exists() else []
 except (OSError,ValueError) as exc:raise SystemExit("Refusing to overwrite unreadable historical global data: "+str(exc))
 rows={x["id"]:x for x in previous+seed if valid(x)}
 status={"started_at":now(),"sources":{},"warning":"No collector reports complete worldwide coverage. FCA and FinCEN are primary records; AUSTRAC currently has manually verified seed entries."}
 with Session() as session:
  session.headers.update(HEADERS)
  offline=os.environ.get("GLOBAL_SOURCES_OFFLINE")=="1"
  for regulator,fn in ([] if offline else [("FinCEN",scan_fincen),("FCA",scan_fca)]):
   try:
    found=fn(session)
    for e in found:
     if valid(e):
      e["first_seen_at"]=rows.get(e["id"],{}).get("first_seen_at",now())
      rows[e["id"]]=e
    status["sources"][regulator]={"status":"ok" if found else "empty","new_snapshot_rows":len(found),"kind":"official_decision_index"}
   except Exception as e:
    status["sources"][regulator]={"status":"failed","error":str(e)[:240],"kind":"official_decision_index"}
 if offline:status["sources"]["FinCEN"]={"status":"offline_test_uses_seed"};status["sources"]["FCA"]={"status":"offline_test_uses_seed"}
 for agency in ("AUSTRAC","HKMA","MAS","Central Bank of Ireland","OFAC"):
  status["sources"][agency]={"status":"seed_verified","kind":"manual_source_verified",
    "records":sum(x.get("regulator")==agency for x in seed)}

 # Unknown currencies are not converted, and duplicate agencies remain separate
 # with their own regulator and notice ID.
 # When the seed has a source-reviewed assessment with penalty and legal
 # context, combine its corresponding index entry rather than double-counting
 # one agency action (e.g. the same FinCEN TD settlement or FCA fine).
 def significant_words(value):
  return set(w for w in re.findall(r"[a-z]{2,}",str(value or "").lower())
             if w not in {"the","and","matter","bank","inc","usa","limited","holdings"})
 seeds=[x for x in rows.values() if x.get("is_seed")]
 for item_id,item in list(rows.items()):
  if item.get("is_seed") or item.get("regulator") not in ("FinCEN","FCA"):continue
  for seed_row in seeds:
   if seed_row.get("regulator")!=item["regulator"] or seed_row.get("published_at")!=item.get("published_at"):
    continue
   aa=significant_words(seed_row.get("institution"))
   bb=significant_words(item.get("institution"))
   if aa and bb and len(aa&bb)/max(1,min(len(aa),len(bb)))>=.67:
    if item["source_url"]!=seed_row["source_url"]:
     seed_row.setdefault("additional_source_urls",[])
     if item["source_url"] not in seed_row["additional_source_urls"]:
      seed_row["additional_source_urls"].append(item["source_url"])
    del rows[item_id]
    break
 items=sorted(rows.values(),key=lambda x:x.get("published_at") or "",reverse=True)
 OUTPUT.write_text(json.dumps({"updated_at":now(),"events":items,
   "methodology":"Official-source actions for USA, UK and Australia only; regulator-country center is a jurisdiction locator, not an incident location. No currency conversion. Separate agencies may publish overlapping settlements. Dynamic regulator feeds are best-effort; consult source health."},ensure_ascii=False,indent=2)+"\n","utf-8")
 status["completed_at"]=now()
 status["total_global_events"]=len(items)
 STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n","utf-8")
 print(json.dumps({"source_status":status["sources"],"total_global_events":len(items)}))
if __name__=="__main__":
 run()
