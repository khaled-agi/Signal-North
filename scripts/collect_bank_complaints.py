#!/usr/bin/env python3
"""Refresh National Bank complaint disclosures from bank-published HTML.

Updates only on a defensible parse. Never treats a blocked page as zero cases.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import tempfile
import os
import requests
from bs4 import BeautifulSoup

URL="https://www.nbc.ca/about-us/governance/complaint-settlement.html"
ARCHIVE=Path("data/bank_complaint_disclosures.json")
STATUS=Path("data/bank_disclosure_source_health.json")

def parse_national_bank(html):
 text=" ".join(BeautifulSoup(html,"html.parser").get_text(" ",strip=True).split())
 section=re.search(r"\bAnnual Data\b(.{0,4000})",text,re.I)
 if not section:raise ValueError("Annual Data not found")
 payload=section.group(1)
 year_match=re.search(r"\b(20(?:2[4-9]|3[0-5]))\b",payload[:90])
 count_match=re.search(r"Number of complaints reviewed by the Client Complaint Appeal Office\s+([\d,]+)",payload,re.I)
 if not year_match or not count_match:raise ValueError("Annual data year or count unavailable")
 year=int(year_match.group(1));count=int(count_match.group(1).replace(",",""))
 if not 100<=count<=250000:raise ValueError("Complaint count outside sanity bounds")
 pct_match=re.search(r"Main reason for complaint.{0,250}?Fraud\s+(\d+(?:\.\d+)?)\s*%",payload,re.I)
 return {"id":f"national-bank-{year}","institution":"National Bank of Canada",
         "year":year,"report_name":f"Client Complaint Appeal Office Annual Data {year}",
         "office":"CCAO","scope":"Complaints reviewed including those outside mandate",
         "metric_name":"complaints_reviewed_including_out_of_mandate",
         "metric_value":count,"source_url":URL,"source_type":"official_bank_public_disclosure",
         **({"fraud_nature_pct":float(pct_match.group(1))} if pct_match else {})}

def atomic(obj,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as file:
  json.dump(obj,file,ensure_ascii=False,indent=2)
  tmp=file.name
 os.replace(tmp,path)

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 health={"source":"National Bank of Canada","url":URL,"last_attempt":now}
 try:
  resp=requests.get(URL,timeout=35,headers={"User-Agent":"SignalNorthPublicResearch/1.0"})
  resp.raise_for_status()
  record=parse_national_bank(resp.text)
  archive=json.loads(ARCHIVE.read_text(encoding="utf-8"))
  existing={x["id"]:x for x in archive["records"]}
  # Preserve vetted historic figures and richer annotations.
  existing[record["id"]]={**existing.get(record["id"],{}),**record}
  archive["records"]=sorted(existing.values(),key=lambda x:(x["institution"],x["year"]))
  archive["metadata"]["last_live_update"]=now
  atomic(archive,ARCHIVE)
  health.update({"status":"success","record_id":record["id"],"metric_value":record["metric_value"]})
 except Exception as exc:
  health.update({"status":"failed_last_good_preserved","error_type":type(exc).__name__})
 atomic(health,STATUS)
 print(json.dumps(health))
if __name__=="__main__":main()
