#!/usr/bin/env python3
"""Collect public metadata links from Canadian publisher RSS feeds.

These are headline-only discovery references; article text, images, and RSS
descriptions are NOT copied to the public dataset.
"""
from __future__ import annotations
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
import requests

from collect_news import headline_claims,headline_location,classify,normalize
from collect_sources import CRIME

DATA=Path(__file__).resolve().parents[1]/"data"
OUT=DATA/"publisher_news.json"
HEALTH=DATA/"publisher_source_status.json"
FEEDS={
 "Global News Canada":("https://globalnews.ca/canada/feed/","globalnews.ca"),
 "Financial Post":("https://financialpost.com/feed/","financialpost.com"),
 "National Post":("https://nationalpost.com/feed/","nationalpost.com"),
}
HEADERS={"User-Agent":"SignalNorthResearch/0.5 (+https://github.com/khaled-agi/Signal-North; headline metadata only)"}

def stamp():return datetime.now(timezone.utc).isoformat(timespec="seconds")

def parse_date(raw):
 if not raw:return None
 try:
  dt=parsedate_to_datetime(raw)
  if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
  return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
 except (TypeError,ValueError,OverflowError):
  try:return datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(timezone.utc).isoformat(timespec="seconds")
  except (TypeError,ValueError):return None

def feed_rows(xml):
 root=ET.fromstring(xml)
 atom="{http://www.w3.org/2005/Atom}"
 rss=root.findall(".//channel/item")
 if rss:
  for x in rss:
   yield normalize(x.findtext("title")),normalize(x.findtext("link")),parse_date(x.findtext("pubDate"))
 else:
  for x in root.findall(".//"+atom+"entry"):
   link_el=x.find(atom+"link")
   link=link_el.get("href","") if link_el is not None else ""
   yield normalize(x.findtext(atom+"title")),normalize(link),parse_date(x.findtext(atom+"published") or x.findtext(atom+"updated"))

def run():
 DATA.mkdir(exist_ok=True,parents=True)
 try:old=json.loads(OUT.read_text("utf-8")).get("leads",[]) if OUT.exists() else []
 except (ValueError,OSError) as exc:raise SystemExit("Cannot read prior publisher history: "+str(exc))
 found={x["id"]:x for x in old}
 health={"completed_at":None,"sources":{}}
 for name,(feed,hostname) in FEEDS.items():
  try:
   r=requests.get(feed,headers=HEADERS,timeout=30)
   r.raise_for_status()
   rows=list(feed_rows(r.content))
   count=0
   for title,link,published in rows[:120]:
    if not title or not CRIME.search(title) or not published:continue
    u=urlparse(link)
    if u.scheme!="https" or not (u.hostname==hostname or u.hostname.endswith("."+hostname)):continue
    key=hashlib.sha256((name.casefold()+"|"+title.casefold()).encode()).hexdigest()[:20]
    before=found.get(key,{})
    geo=headline_location(title)
    found[key]={
     "id":key,"title":title,"url":link,"publisher":name,
     "published_at":published,"date_basis":"publisher_rss_publication",
     "discovery_source":"publisher_rss","topics":["Canadian publisher financial crime coverage"],
     "category":classify(title),"evidence_status":"unverified_news_lead",
     "institution":None,"reported_loss":None,
     "content_kind":"news_lead",
     "geographic_accuracy":"headline_only" if geo else "not_geocoded",
     **headline_claims(title),**geo,
     "first_seen_at":before.get("first_seen_at",stamp()),"last_observed_at":stamp(),
     "notice":"Public article title and source metadata only. The linked full article has not been checked for bank responsibility or actual losses."
    }
    count+=1
   health["sources"][name]={"status":"ok","feed_items":len(rows),"accepted":count,"url":feed}
  except Exception as exc:
   health["sources"][name]={"status":"failed","error":str(exc)[:250],"url":feed}
 all_records=sorted(found.values(),key=lambda x:x.get("published_at") or "",reverse=True)[:1400]
 OUT.write_text(json.dumps({"updated_at":stamp(),"leads":all_records},indent=2,ensure_ascii=False)+"\n","utf-8")
 health["completed_at"]=stamp();health["cumulative_records"]=len(all_records)
 HEALTH.write_text(json.dumps(health,indent=2)+"\n","utf-8")
 print(json.dumps(health,indent=2))
if __name__=="__main__":run()
