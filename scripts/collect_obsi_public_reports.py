#!/usr/bin/env python3
"""Catalogue OBSI's published quarterly and annual source documents.

This is an official public-source report feed; NOT a firm-level Power BI export.
No confidential OBSI client data are fetched or retained.
"""
import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup
import requests

PAGES={
 "quarterly":"https://www.obsi.ca/en/case-data-insights/quarterly-case-data/",
 "annual":"https://www.obsi.ca/en/news-publications/annual-reports/",
}
OUTPUT=Path("data/obsi_public_report_catalog.json")
def extract_documents(html,url,category):
 soup=BeautifulSoup(html,"html.parser")
 found={}
 for anchor in soup.select("a[href]"):
  name=" ".join(anchor.get_text(" ",strip=True).split())
  href=urljoin(url,anchor["href"]).split("#")[0]
  host=urlparse(href).hostname or ""
  if not host.endswith(("obsi.ca","govstack.com")) or ".pdf" not in href.lower():continue
  if not re.search(r"\b(?:20\d\d|q[1-4]|quarter|fiscal|annual)\b",name,re.I):continue
  id=category+"-"+re.sub(r"[^a-z0-9]+","-",name.casefold()).strip("-")[:90]
  if not id:continue
  found[id]={"id":id,"label":name[:160],"source_url":href,"type":category,
             "report_year":int(re.search(r"\b(20\d\d)\b",name).group(1)) if re.search(r"\b(20\d\d)\b",name) else None,
             "source":"OBSI official public reports"}
 return list(found.values())

def main():
 previous={"documents":[],"source_health":{}}
 if OUTPUT.exists():
  try:previous=json.loads(OUTPUT.read_text("utf-8"))
  except (OSError,ValueError):pass
 health=dict(previous.get("source_health",{}))
 bytype={}
 for x in previous.get("documents",[]):bytype.setdefault(x.get("type"),[]).append(x)
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 with requests.Session() as session:
  session.headers.update({"User-Agent":"SignalNorthResearch/1.0 (public OBSI reports only)"})
  for category,url in PAGES.items():
   try:
    response=session.get(url,timeout=25);response.raise_for_status()
    found=extract_documents(response.text,url,category)
    if len(found)<(6 if category=="annual" else 12):
     raise ValueError(f"Only {len(found)} official links found")
    bytype[category]=found
    health[category]={"status":"success","last_success":now,"records":len(found),"url":url}
   except Exception as exc:
    health[category]={**health.get(category,{}),"status":"failed_previous_preserved" if bytype.get(category) else "unavailable","last_check":now,"error_type":type(exc).__name__,"url":url}
 documents=sorted([item for records in bytype.values() for item in records],key=lambda x:(x["type"],x["report_year"] or 0,x["label"]),reverse=True)
 output={"generated_at":now,"source_health":health,"documents":documents,
         "scope":"Historical source-document catalog; numerical OBSI firm/year Data Cube export NOT available through this feed.",
         "methodology":"Documents are linked from OBSI's own annual/quarterly report pages; counts are PDF links, not complaint counts."}
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=OUTPUT.parent,encoding="utf-8",delete=False) as file:
  json.dump(output,file,ensure_ascii=False,indent=2)
  tmp=file.name
 os.replace(tmp,OUTPUT)
 print(json.dumps({"documents":len(documents),"source_health":health}))
if __name__=="__main__":main()
