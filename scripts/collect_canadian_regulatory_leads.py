#!/usr/bin/env python3
"""Collect official enforcement index links as research leads, not adjudicated case data."""
import json, os, re, tempfile, urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from pathlib import Path

SOURCES = [
 {"id":"fintrac","agency":"FINTRAC","url":"https://fintrac-canafe.canada.ca/pen/4-eng","type":"enforcement","keywords":["penalty","monetary","administrative"]},
 {"id":"fcac","agency":"FCAC","url":"https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html","type":"enforcement","keywords":["decision","proceeding","summary"]},
 {"id":"ciro","agency":"CIRO","url":"https://www.ciro.ca/enforcement","type":"enforcement","keywords":["enforcement","decision","disciplin"]},
 {"id":"osc","agency":"OSC","url":"https://www.osc.ca/en/enforcement","type":"enforcement","keywords":["enforcement","decision","settlement","proceeding"]},
 {"id":"amf","agency":"AMF","url":"https://lautorite.qc.ca/en/","type":"enforcement","keywords":["decision","sanction","enforcement","penalt"]},
 {"id":"bcsc","agency":"BCSC","url":"https://www.bcsc.bc.ca/","type":"enforcement","keywords":["enforcement","decision","sanction"]},
 {"id":"asc","agency":"ASC","url":"https://www.asc.ca/","type":"enforcement","keywords":["enforcement","decision","order"]},
 {"id":"csa","agency":"CSA","url":"https://www.securities-administrators.ca/csa-activities/enforcement/disciplined-list/","type":"enforcement","keywords":["disciplined","enforcement","decision"]},
]
class Anchors(HTMLParser):
 def __init__(self):
  super().__init__();self.links=[];self.href=None;self.words=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a": self.href=dict(attrs).get("href");self.words=[]
 def handle_data(self,data):
  if self.href is not None:self.words.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.href is not None:
   self.links.append((self.href," ".join(" ".join(self.words).split())))
   self.href=None;self.words=[]

def collect(source):
 req=urllib.request.Request(source["url"],headers={"User-Agent":"SignalNorthResearch/1.0 (public-source-index)","Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=30) as resp:
  raw=resp.read(3_000_001)
  if len(raw)>3_000_000:raise ValueError("HTML index exceeds 3 MB safety limit")
  html=raw.decode("utf-8",errors="replace")
 parser=Anchors();parser.feed(html)
 origin=urlparse(source["url"]).netloc.lower().removeprefix("www.")
 seen=set();out=[]
 for href,title in parser.links:
  url=urljoin(source["url"],href);host=urlparse(url).netloc.lower().removeprefix("www.")
  if not url.startswith("https://") or not (host==origin or host.endswith("."+origin)):continue
  if not title or len(title)<6 or len(title)>350:continue
  if url in seen or url.rstrip("/")==source["url"].rstrip("/"):continue
  keywords=source["keywords"];hay=(title+" "+url).lower()
  if not any(k in hay for k in keywords):continue
  seen.add(url)
  out.append({"agency":source["agency"],"source_id":source["id"],"title":title,"url":url,"classification":"official_index_link_unreviewed"})
 if not out:raise ValueError("No matching source-linked records; retaining previous snapshot")
 return out[:500]

def main():
 path=Path("data/canadian_regulatory_leads.json")
 old={"leads":[],"sources":{}}
 if path.exists():
  try:old=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,ValueError):pass
 records={s["id"]:[r for r in old.get("leads",[]) if r.get("source_id")==s["id"]] for s in SOURCES}
 state=dict(old.get("sources",{}));now=datetime.now(timezone.utc).isoformat()
 for source in SOURCES:
  sid=source["id"]
  try:
   items=collect(source);records[sid]=items
   state[sid]={"status":"success","last_success":now,"count":len(items),"index_url":source["url"]}
   print(sid,"collected",len(items))
  except Exception as e:
   state[sid]={**state.get(sid,{}),"status":"failed_previous_preserved" if records[sid] else "unavailable","last_check":now,"error_type":type(e).__name__,"index_url":source["url"]}
   print(sid,"FAILED:",type(e).__name__,str(e)[:120])
 output={"generated_at":now,"unit":"official_index_link_unreviewed","note":"Links are discovery leads. They are not verified enforcement actions or evidence of wrongdoing. Only read original documents for case findings.", "sources":state,"leads":[r for s in SOURCES for r in records[s["id"]]]}
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as f:
  json.dump(output,f,ensure_ascii=False,indent=2);temp=f.name
 os.replace(temp,path)
if __name__=="__main__":main()
