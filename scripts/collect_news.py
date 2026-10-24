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
    if not title or not link.startswith("https://"):continue
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
      "geographic_accuracy":"not_geocoded",
      "institution":None,"reported_loss":None,
      "notice":"Headline discovery only. Open and assess the original publication before attributing loss, guilt or operational weakness."
    }
    count+=1
   success+=1
   status["sources"][topic]={"status":"ok" if items else "empty_feed","returned":len(items),"accepted":count}
  except Exception as exc:
   status["sources"][topic]={"status":"failed","error":str(exc)[:250]}
 leadlist=sorted(by_id.values(),key=lambda x:x.get("published_at") or "",reverse=True)[:400]
 FEED.write_text(json.dumps({"updated_at":stamp(),"leads":leadlist},ensure_ascii=False,indent=2)+"\n","utf-8")
 status["stored_leads"]=len(leadlist)
 status["last_completed_at"]=stamp()
 STATUS.write_text(json.dumps(status,indent=2)+"\n","utf-8")
 print(json.dumps({"leads":len(leadlist),"feeds_ok":success,"feeds_total":len(QUERIES),"status":status["sources"]},indent=2))
 return 0 if success or leadlist else 1

if __name__=="__main__":sys.exit(collect())
