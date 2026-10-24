#!/usr/bin/env python3
"""Discover Canadian fraud news as *unverified research leads* via syndicated RSS.

Do not infer that any named bank committed fraud or suffered a loss from a headline.
No article content is republished; links and original publisher metadata are retained.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from email.utils import parsedate_to_datetime

import requests
from collect import CITIES, PROVINCE_CODES

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
FEED=DATA/"news.json"
STATUS=DATA/"news_status.json"
QUERIES={
 "Bank and customer fraud":'"bank" "fraud" "Canada" when:14d',
 "Scams and victims":'"scam" "victims" "Canada" when:14d',
 "Police investigations":'"fraud" "charged" "Ontario" OR "Quebec" when:14d',
 "Money laundering":'"money laundering" "Canada" "bank" when:14d',
 "Investment schemes":'"investment scam" "Canada" when:14d',
 "Québec fraude":'"fraude" "banque" "Québec" when:14d',
 "Credit unions and fintech":'"credit union" "fraud" "Canada" when:14d',
 "Fraud research and reports":'"fraud" "Canada" ("report" OR "study" OR "research") when:30d',
}
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; SignalNorthResearch/0.2; public news discovery)"}

def stamp():
 return datetime.now(timezone.utc).isoformat(timespec="seconds")
def parse_date(raw):
 try:
  dt=parsedate_to_datetime(raw)
  if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
  return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
 except (ValueError,TypeError):return None
def normalize(x):
 return re.sub(r"\s+"," ",x or "").strip()
def classify(title):
 t=title.lower()
 for words,category in [
  (["money laundering","blanchiment"],"AML and laundering"),
  (["cyberattack","ransomware","data breach","cybersecurity"],"Cyber and account compromise"),
  (["investment","crypto","securities","placement"],"Investment fraud"),
  (["romance","relationship"],"Relationship scam"),
  (["mule"],"Money mule activity"),
  (["scam","arnaque","escroquerie"],"Scam and victim reports"),
  (["fraud","fraude"],"Reported fraud")]:
  if any(w in t for w in words):return category
 return "Financial crime watch"
DOMESTIC_PUBLISHERS = (
 "cbc", "ctv", "global news", "toronto star", "financial post", "the globe and mail",
 "citynews", "montreal gazette", "ottawa citizen", "vancouver sun", "la presse",
 "radio-canada", "tva nouvelles", "le devoir", "national post", "canadian press",
 "the canadian press", "bnnbloomberg", "bnn bloomberg", "calgary herald",
 "edmonton journal", "winnipeg free press", "halifax examiner", "sasktoday",
 "canada newswire", "the record", "the tyee", "saltwire", "the logic",
)
DOMESTIC_MARKERS = (
 "canada", "canadian", "ontario", "toronto", "ottawa", "québec", "quebec",
 "montreal", "montréal", "alberta", "calgary", "edmonton", "manitoba",
 "winnipeg", "british columbia", "vancouver", "surrey", "saskatchewan",
 "regina", "saskatoon", "nova scotia", "halifax", "new brunswick",
 "newfoundland", "pei", "prince edward island", "rcmp", "opp", "fintrac",
 "fcac", "bmo", "cibc", "scotiabank", "rbc", "td bank", "interac",
 "fraude bancaire", "gendarmerie royale", "police provinciale",
)
CRIME_MARKERS = (
 "fraud", "fraude", "scam", "escroquerie", "arnaque", "money laundering",
 "blanchiment", "phishing", "charged", "arrested", "investment scheme",
 "cyberattack", "ransomware", "data breach", "stolen", "theft",
 "extortion", "identity theft", "fraudulent", "deceptive marketing",
 "sanction", "amende", "penalty", "illicit", "money mule",
 "forged", "impersonation", "hacked", "unauthorized", "laundering",
)
FOREIGN_MARKERS = (
 "mumbai", "sharjah", "dubai", "pakistan", "new delhi", "bengaluru",
 "india", "bangladesh", "lagos", "nigeria", "philippines", "kenya",
 "london uk", "south africa", "united kingdom", "australia",
)

def relevant(title: str, publisher: str) -> bool:
 t=title.casefold()
 p=publisher.casefold()
 if not any(word in t for word in CRIME_MARKERS):
  return False
 domestic=any(word in t for word in DOMESTIC_MARKERS)
 if any(word in t for word in FOREIGN_MARKERS) and not domestic:
  return False
 return domestic or any(name in p for name in DOMESTIC_PUBLISHERS)

def headline_location(title: str) -> dict:
 """City literally named in the headline — never inferred event location."""
 for (city, province), (lat, lon) in sorted(CITIES.items(), key=lambda item: -len(item[0][0])):
  if re.search(r"(?<!\w)"+re.escape(city)+r"(?!\w)", title, re.I):
   return {"map_location": f"{city}, {province}",
           "map_latitude": lat, "map_longitude": lon,
           "map_province": PROVINCE_CODES[province],
           "map_role": "headline city mention only; incident location unverified"}
 return {}


BANK_ALIASES = (
 ("TD", ("td bank", "td canada trust", "toronto-dominion")),
 ("RBC", ("rbc", "royal bank of canada")),
 ("Scotiabank", ("scotiabank", "bank of nova scotia")),
 ("BMO", ("bmo", "bank of montreal")),
 ("CIBC", ("cibc",)),
 ("Tangerine", ("tangerine bank", "tangerine")),
 ("National Bank", ("national bank of canada",)),
 ("Desjardins", ("desjardins",)),
 ("Simplii", ("simplii financial",)),
)
HEADLINE_CASE_HINTS=("customer","client","victim","resident","woman","man ","family","lost","loses","defrauded","stolen","unauthorized","identity stolen","scammed","scam victim","account drained")

def headline_claims(title: str) -> dict:
 """Non-verified headline-only cues, never finalized institutional attribution."""
 t=title.casefold()
 banks=[name for name,aliases in BANK_ALIASES if any(re.search(r"(?<!\w)"+re.escape(a)+r"(?!\w)",t) for a in aliases)]
 matches=re.findall(r"(?:C\$|CAD\s*|\$)\s*[\d,]+(?:\.\d+)?\s*(?:million|billion|[mMkK])?\b",title,re.I)
 is_case=any(w in t for w in HEADLINE_CASE_HINTS)
 is_research=bool(re.search(r"\b(?:research|study|industry report|annual report|survey|whitepaper|white paper)\b",t))
 return {"banks_mentioned_in_headline":banks,"amount_strings_in_headline":matches[:3],
         "headline_case_candidate":is_case,"content_kind":"research_report_lead" if is_research else "news_lead",
         "extraction_provenance":"headline only; bank role, incident date, amount type and currency not verified"}

def collect():
 DATA.mkdir(parents=True,exist_ok=True)
 try:
  old=json.loads(FEED.read_text("utf-8")).get("leads",[]) if FEED.exists() else []
 except (ValueError,TypeError) as e:
  raise SystemExit("Refusing to replace corrupted news history: "+str(e))
 by_id={e["id"]:e for e in old}
 status={"last_attempt_at":stamp(),"sources":{}}
 success=0
 for topic,query in QUERIES.items():
  url="https://news.google.com/rss/search?"+urlencode({"q":query,"hl":"en-CA","gl":"CA","ceid":"CA:en"})
  try:
   resp=requests.get(url,headers=HEADERS,timeout=30)
   resp.raise_for_status()
   root=ET.fromstring(resp.content)
   items=root.findall(".//channel/item")
   count=0
   for item in items[:50]:
    title=normalize(item.findtext("title"))
    link=normalize(item.findtext("link"))
    published=parse_date(item.findtext("pubDate"))
    source=item.find("source")
    publisher=normalize(source.text) if source is not None else "Syndicated news"
    if not title or not link.startswith("https://") or not relevant(title,publisher):continue
    if published:
     age=datetime.now(timezone.utc)-datetime.fromisoformat(published)
     if age>timedelta(days=90):continue
    key=hashlib.sha256((publisher+"|"+title.lower()).encode()).hexdigest()[:20]
    oldlead=by_id.get(key,{})
    by_id[key]={
      "id":key,"title":title,"url":link,"publisher":publisher,
      "published_at":published,"first_seen_at":oldlead.get("first_seen_at",stamp()),
      "last_observed_at":stamp(),"topics":sorted(set(oldlead.get("topics",[])+[topic])),
      "category":classify(title),"evidence_status":"unverified_news_lead",
      "geographic_accuracy":"headline_only" if headline_location(title) else "not_geocoded",
      **headline_location(title),
      **headline_claims(title),
      "institution":None,"reported_loss":None,
      "notice":"Headline discovery only. Open and assess the original publication before attributing loss, guilt or operational weakness."
    }
    count+=1
   success+=1
   status["sources"][topic]={"status":"ok" if items else "empty_feed","returned":len(items),"accepted":count}
  except Exception as exc:
   status["sources"][topic]={"status":"failed","error":str(exc)[:250]}
 for lead in by_id.values():
  for field in ("map_location","map_latitude","map_longitude","map_province","map_role"):
   lead.pop(field,None)
  lead.update(headline_location(lead.get("title","")))
  lead["geographic_accuracy"]="headline_only" if lead.get("map_location") else "not_geocoded"
  lead.update(headline_claims(lead.get("title","")))
 leadlist=sorted((item for item in by_id.values() if relevant(item.get("title",""),item.get("publisher",""))),key=lambda x:x.get("published_at") or "",reverse=True)[:400]
 FEED.write_text(json.dumps({"updated_at":stamp(),"leads":leadlist},ensure_ascii=False,indent=2)+"\n","utf-8")
 status["stored_leads"]=len(leadlist)
 status["last_completed_at"]=stamp()
 STATUS.write_text(json.dumps(status,indent=2)+"\n","utf-8")
 print(json.dumps({"leads":len(leadlist),"feeds_ok":success,"feeds_total":len(QUERIES),"status":status["sources"]},indent=2))
 return 0 if success or leadlist else 1

if __name__=="__main__":sys.exit(collect())
