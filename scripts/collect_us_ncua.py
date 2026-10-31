#!/usr/bin/env python3
"""Ingest the official NCUA quarterly active credit-union roster from FOICU.txt.

NCUA provides final quarterly ZIPs of call-report CSV tables. Preserve
NCUA CU_NUMBER as identifier; never match by institution name alone.
"""
from __future__ import annotations
import csv
import io
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

INDEX="https://ncua.gov/analysis/credit-union-corporate-call-report-data/quarterly-data"
OUT=Path("data/us_ncua_credit_unions.json")
HEALTH=Path("data/us_ncua_source_health.json")
MAX_BYTES=80_000_000

def find_latest_zip(html):
    soup=BeautifulSoup(html,"html.parser")
    available={}
    for a in soup.select("a[href]"):
        href=urljoin(INDEX,a["href"])
        host=urlparse(href).hostname or ""
        m=re.search(r"call-report-data-(20\d\d)-(03|06|09|12)\.zip(?:\?|$)",href,re.I)
        if m and host.endswith("ncua.gov"):
            available[(int(m.group(1)),int(m.group(2)))]=href.split("?")[0]
    if not available:
        raise ValueError("No final NCUA quarterly ZIP listed on its official page")
    year,month=max(available)
    return year,month,available[(year,month)]

def parse_roster(content,year,month):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        selected=[n for n in archive.namelist() if n.split("/")[-1].casefold()=="foicu.txt"]
        if len(selected)!=1:
            raise ValueError(f"FOICU.txt not unique or missing ({len(selected)})")
        if archive.getinfo(selected[0]).file_size>15_000_000:
            raise ValueError("NCUA roster is unexpectedly large")
        raw=archive.read(selected[0])
    try:
        text=raw.decode("utf-8-sig")
    except UnicodeError:
        text=raw.decode("cp1252")
    rows=csv.DictReader(io.StringIO(text))
    if not rows.fieldnames:
        raise ValueError("NCUA CSV missing headers")
    mapping={str(k).strip().upper():k for k in rows.fieldnames}
    if not {"CU_NUMBER","CU_NAME"}.issubset(mapping):
        raise ValueError("Unexpected NCUA FOICU headers")
    def get(r,name):
        return str(r.get(mapping.get(name,""),"") or "").strip()
    result={}
    for row in rows:
        number=get(row,"CU_NUMBER")
        name=get(row,"CU_NAME")
        if number.endswith(".0"):number=number[:-2]
        if not number.isdigit() or not name:
            continue
        cu_type=get(row,"CU_TYPE")
        if cu_type=="3":
            continue # NCUA type 3: state chartered, not federally insured
        if number in result:
            raise ValueError("NCUA duplicate CU_NUMBER")
        result[number]={
            "ncua_charter":number,
            "institution":name[:250],
            "city":get(row,"CITY")[:120],
            "state":get(row,"STATE")[:50],
            "country":"US",
            "cu_type":cu_type or None,
            "fed_rssd":get(row,"RSSD") or None,
            "cycle":f"{year}-{month:02d}",
            "source_kind":"official_NCUA_quarterly_credit_union_roster",
        }
    if not 3500<=len(result)<=8000:
        raise ValueError(f"NCUA roster unexpectedly has {len(result)} records")
    return list(result.values())

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
        json.dump(value,f,ensure_ascii=False,separators=(",",":"))
        staging=f.name
    os.replace(staging,path)

def main():
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    old={}
    if HEALTH.exists():
        try:old=json.loads(HEALTH.read_text("utf-8"))
        except (ValueError,OSError):pass
    if OUT.exists() and old.get("status")=="success" and old.get("last_success","")[:10]==now[:10] and os.getenv("SIGNALNORTH_FORCE_NCUA")!="1":
        print("NCUA quarterly roster snapshot already collected today")
        return
    status={"last_attempt":now,"index_url":INDEX}
    try:
        session=requests.Session()
        resp=session.get(INDEX,timeout=35)
        resp.raise_for_status()
        year,month,url=find_latest_zip(resp.text)
        with session.get(url,timeout=100,stream=True) as r:
            r.raise_for_status()
            chunks=[];size=0
            for chunk in r.iter_content(65536):
                size+=len(chunk)
                if size>MAX_BYTES:
                    raise ValueError("NCUA quarterly ZIP exceeds safe limit")
                chunks.append(chunk)
        records=parse_roster(b"".join(chunks),year,month)
        atomic(OUT,{"source":"NCUA published final quarterly call reports",
                    "source_url":url,"index_url":INDEX,"cycle":f"{year}-{month:02d}",
                    "retrieved_at":now,"record_count":len(records),
                    "jurisdiction":"US","unit":"federally_insured_credit_union",
                    "methodology":"NCUA CU_NUMBER is stable entity ID. Inclusion is a regulatory listing, not a fraud or enforcement signal.",
                    "records":records})
        status.update({"status":"success","source_url":url,"last_success":now,"count":len(records)})
        print(f"NCUA FOICU: {len(records)} active credit unions (cycle {year}-{month:02d})",flush=True)
    except Exception as exc:
        status.update({"status":"failed_last_good_preserved" if OUT.exists() else "unavailable",
                       "error_type":type(exc).__name__,"detail":str(exc)[:230]})
        print(f"NCUA FOICU FAILED: {type(exc).__name__}: {exc}",flush=True)
    atomic(HEALTH,status)

if __name__=="__main__":
    main()
