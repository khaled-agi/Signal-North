#!/usr/bin/env python3
"""Collect the AMF open licensed-entity dataset via Données Québec CKAN metadata.

The AMF regulator website may block crawler traffic; this uses its official
CC-BY government open-data publication. Registry membership is not misconduct.
"""
import csv,hashlib,io,json,os,tempfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlparse
import requests

PACKAGE="liste-des-institutions-financieres-et-agences-d-evaluation-du-credit"
API="https://www.donneesquebec.ca/recherche/api/3/action/package_show"
OUT=Path("data/amf_quebec_entities.json")
LIMIT=15_000_000

def choose_resource(resources):
 options=[r for r in resources if str(r.get("format","")).upper()=="CSV" and
          any(k in str(r.get("name","")).casefold() for k in ("liste","institutions","agents","list"))]
 if not options:raise ValueError("AMF institutions CSV not found in CKAN package")
 return options[0]

def parse_csv(content):
 text=None
 for enc in ("utf-8-sig","utf-16","cp1252"):
  try:text=content.decode(enc);break
  except UnicodeError:pass
 if text is None:raise ValueError("Cannot decode official AMF CSV")
 sample=text[:4000]
 dialect=csv.Sniffer().sniff(sample,delimiters=",;\t")
 reader=csv.DictReader(io.StringIO(text),dialect=dialect)
 if not reader.fieldnames or len(reader.fieldnames)<3:raise ValueError("Unexpected AMF schema")
 records=[]
 for row in reader:
  fields={str(k).strip():str(v or "").strip()[:450] for k,v in row.items() if k and v is not None}
  if not any(fields.values()):continue
  rid=hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
  records.append({"id":rid,"fields":fields})
 if len(records)<50:raise ValueError("AMF open CSV under minimum expected rows")
 return {"columns":reader.fieldnames,"records":records}

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 health={"source":"AMF via Données Québec","last_attempt":now,"dataset":PACKAGE}
 try:
  response=requests.get(API,params={"id":PACKAGE},timeout=30);response.raise_for_status()
  meta=response.json()
  if meta.get("success") is not True:raise ValueError("CKAN package lookup failed")
  obj=meta["result"];res=choose_resource(obj.get("resources",[]))
  url=res.get("url","");host=urlparse(url).hostname or ""
  # Government open data metadata supplies canonical resource download.
  if not url.startswith("https://") or not host.endswith(("donneesquebec.ca","quebec.ca","lautorite.qc.ca")):
   raise ValueError("AMF download is not on a recognized Quebec government domain")
  with requests.get(url,timeout=60,stream=True) as r:
   r.raise_for_status()
   chunks=[];size=0
   for c in r.iter_content(65536):
    size+=len(c)
    if size>LIMIT:raise ValueError("AMF CSV exceeds maximum size")
    chunks.append(c)
  parsed=parse_csv(b"".join(chunks))
  result={"retrieved_at":now,"source":"AMF official Quebec open data",
          "source_url":url,"catalog_url":"https://www.donneesquebec.ca/recherche/dataset/"+PACKAGE,
          "license":obj.get("license_title","CC-BY 4.0"),
          "record_count":len(parsed["records"]),"columns":parsed["columns"],
          "records":parsed["records"],
          "methodology":"Regulated financial institutions and credit reporting agents; no enforcement finding implied."}
  OUT.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile("w",dir=OUT.parent,encoding="utf-8",delete=False) as file:
   json.dump(result,file,ensure_ascii=False,indent=2)
   tmp=file.name
  os.replace(tmp,OUT)
  health.update({"status":"success","record_count":result["record_count"],"source_url":url})
 except Exception as e:
  health.update({"status":"failed_last_good_preserved","error_type":type(e).__name__})
 path=Path("data/amf_quebec_source_health.json");path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(health,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(health))
if __name__=="__main__":main()
