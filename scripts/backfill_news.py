#!/usr/bin/env python3
"""One-time calendar-month discovery of Canadian fraud reporting via Google News RSS.

An archive of *headlines*, not verified incident records. Searches may be incomplete
or unavailable; preserves source, publication date, query, and source limitations.
"""
from __future__ import annotations
import calendar
import hashlib
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from collect_news import normalize, parse_date, classify, relevant, headline_claims, headline_location

DATA = Path(__file__).resolve().parents[1]/"data"
ARCHIVE = DATA/"news_archive.json"
STATUS = DATA/"archive_status.json"
YEAR = int(os.getenv("ARCHIVE_YEAR","2026"))
QUERIES = {
 "Bank customer losses": '"bank" "fraud" "Canada"',
 "Scam victims": '"scam" "lost" "Canada"',
 "Police cases": '"fraud" "police" "Ontario" OR "Vancouver"',
 "Investment scams": '"investment" "scam" "Canada"',
 "Québec reports": '"fraude" "banque" "Québec"',
 "Identity theft accounts": '"identity theft" "bank" "Canada"',
 "Ransomware and banking": '"ransomware" "financial" "Canada"',
 "E-transfer losses": '"e-transfer" "scam" "Canada"',
 "Senior victimization": '"senior" "fraud" "Canada"',
 "Investment enforcement": '"investment fraud" "charged" "Canada"',
 "Crypto platform fraud": '"crypto" "scam" "Canada"',
 "Wealthsimple impersonation": '"Wealthsimple" "scam" OR "fraud"',
 "Fintech account scams": '"fintech" "account" "fraud" "Canada"',
 "Casino money laundering": '"casino" "money laundering" "Canada"',
 "Online gambling compliance": '"online gambling" "fraud" "Ontario"',
 "Virtual currency AML": '"virtual currency" "FINTRAC" "penalty"',
 "Securities investor warnings": '"investor alert" "crypto" "Canada"',
 "Romance investment": '"romance" "crypto" "Canada"',
 "Job task scams": '"job scam" "Canada"',
 "Student rental scams": '"rental scam" "Canada"',
 "Recovery scams": '"recovery scam" "Canada"',
 "Social media fraud reports": '"reddit" "scam" "bank" "Canada"',

}
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; SignalNorthResearchHistorical/0.3; noncommercial research)"}
def now():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def main():
 if YEAR < 2020 or YEAR > datetime.now(timezone.utc).year:
  raise SystemExit("ARCHIVE_YEAR must be between 2020 and the current year")
 DATA.mkdir(exist_ok=True)
 if ARCHIVE.exists():
  try: previous=json.loads(ARCHIVE.read_text("utf-8")).get("leads",[])
  except Exception as e:raise SystemExit("History cannot be parsed: "+str(e))
 else: previous=[]
 by_id={x["id"]:x for x in previous}
 now_date=datetime.now(timezone.utc).date()
 diagnostics=[]
 for month in range(1,13):
  start=date(YEAR,month,1)
  if start>now_date:break
  end=(date(YEAR+1,1,1) if month==12 else date(YEAR,month+1,1))
  if end>now_date:end=now_date
  if end<=start:continue
  for topic,base in QUERIES.items():
   # Google's date operators are approximate and incomplete; verify actual publication date.
   q=f"{base} after:{start.isoformat()} before:{end.isoformat()}"
   url="https://news.google.com/rss/search?"+urlencode({"q":q,"hl":"en-CA","gl":"CA","ceid":"CA:en"})
   try:
    response=requests.get(url,headers=HEADERS,timeout=18)
    response.raise_for_status()
    feed=ET.fromstring(response.content)
    articles=feed.findall(".//channel/item")
    count=0
    for item in articles[:70]:
     title=normalize(item.findtext("title"))
     link=normalize(item.findtext("link"))
     dt=parse_date(item.findtext("pubDate"))
     src=item.find("source")
     publisher=normalize(src.text) if src is not None else "News syndication"
     if not title or not link.startswith("https://") or not relevant(title,publisher) or not dt:continue
     published=datetime.fromisoformat(dt).date()
     if published<start or published>=end:continue
     key=hashlib.sha256((publisher+"|"+title.casefold()).encode()).hexdigest()[:20]
     original=by_id.get(key,{})
     by_id[key]={**original,
       "id":key,"title":title,"url":link,"publisher":publisher,
       "published_at":dt,"first_seen_at":original.get("first_seen_at",now()),
       "last_observed_at":now(),
       "topics":sorted(set(original.get("topics",[])+[topic])),
       "category":classify(title),"evidence_status":"unverified_news_lead",
       "institution":None,"reported_loss":None,
       "notice":"Syndicated headline only; not an independently verified fraud case.",
       **headline_claims(title),
       **headline_location(title),
       "geographic_accuracy":"headline_only" if headline_location(title) else "not_geocoded",
       "archive_year":YEAR}
     count+=1
    diagnostics.append({"month":start.strftime("%Y-%m"),"topic":topic,"status":"ok","returned":len(articles),"accepted":count})
   except Exception as e:
    diagnostics.append({"month":start.strftime("%Y-%m"),"topic":topic,"status":"failed","error":str(e)[:200]})
   time.sleep(.25)
    # Archive is an additive history; do not replace earlier backfill years.
 results=sorted(by_id.values(),key=lambda x:x.get("published_at") or "",reverse=True)[:4500]
 ARCHIVE.write_text(json.dumps({"updated_at":now(),"leads":results,
    "methodology":"Historical Google News RSS discovery by monthly after/before queries. Coverage is incomplete; publisher publication dates checked. Titles only, unverified."},ensure_ascii=False,indent=2)+"\n","utf-8")
 STATUS.write_text(json.dumps({"last_completed_at":now(),"year_scanned":YEAR,
    "record_count":len(results),"queries":diagnostics},indent=2)+"\n","utf-8")
 print(json.dumps({"year":YEAR,"archive_count":len(results),
   "successful_queries":sum(x["status"]=="ok" for x in diagnostics),
   "failed_queries":sum(x["status"]=="failed" for x in diagnostics)},indent=2))
 if not results:raise SystemExit("No archive records retrieved")
if __name__=="__main__":main()
