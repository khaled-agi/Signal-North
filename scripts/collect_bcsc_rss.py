#!/usr/bin/env python3
"""Official BCSC disciplinary and hearing RSS feed ingestion.

Notice type preserved; allegations and hearings must not be marked sanctions.
"""
import hashlib,json,os,tempfile
import requests
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

FEEDS={
 "disciplined_list":"https://www.bcsc.bc.ca/rss/disciplined-list",
 "hearing_notices":"https://www.bcsc.bc.ca/rss/notices-of-hearing-and-temporary-orders",
}
OUT=Path("data/bcsc_official_rss.json")
def parse_feed(xml,kind):
 root=ET.fromstring(xml)
 items=[]
 for item in root.findall(".//item"):
  get=lambda k:" ".join((item.findtext(k) or "").split())
  title,url,date=get("title"),get("link"),get("pubDate")
  if len(title)<5 or not url.startswith("https://"):continue
  host=urlparse(url).hostname or ""
  if not host.endswith("bcsc.bc.ca"):continue
  k=hashlib.sha256((kind+"|"+url).encode()).hexdigest()[:20]
  items.append({"id":k,"agency":"BCSC","type":kind,
                "title":title[:350],"url":url,"publication_text":date[:100],
                "summary":get("description")[:500],
                "classification":"official_disciplinary_publication" if kind=="disciplined_list" else "official_hearing_or_order_notice",
                "note":"An RSS hearing notice may be an allegation, not an adjudicated sanction."})
 return list({i["id"]:i for i in items}.values())
def save(data):
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=OUT.parent,encoding="utf-8",delete=False) as f:
  json.dump(data,f,ensure_ascii=False,indent=2);p=f.name
 os.replace(p,OUT)
def main():
 old={"records":[],"health":{}}
 if OUT.exists():
  try:old=json.loads(OUT.read_text(encoding="utf-8"))
  except (OSError,ValueError):pass
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 records={x["id"]:x for x in old["records"]}
 health=dict(old.get("health",{}))
 for kind,url in FEEDS.items():
  try:
   r=requests.get(url,timeout=35,headers={"User-Agent":"SignalNorthPublicResearch/1.0"});r.raise_for_status()
   items=parse_feed(r.content,kind)
   if not items:raise ValueError("empty RSS feed")
   for x in items:records[x["id"]]=x
   health[kind]={"status":"success","count_new_feed_items":len(items),"last_success":now,"url":url}
  except Exception as e:
   health[kind]={"status":"failed_last_good_preserved","error_type":type(e).__name__,"last_attempt":now,"url":url}
 output={"generated_at":now,"records":list(records.values())[:2500],"health":health,
         "methodology":"Official BCSC RSS entries only. Hearings are not findings; no attempt to identify named financial institutions from unstructured titles automatically."}
 save(output)
 print(json.dumps({"count":len(output["records"]),"health":health}))
if __name__=="__main__":main()
