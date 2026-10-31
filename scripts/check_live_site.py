#!/usr/bin/env python3
"""Independent public GitHub Pages health verification after deployment."""
import argparse
import json
import re
import time
from urllib.parse import urljoin
from urllib.request import Request, urlopen

REQUIRED = {
    "data/canadian_enforcement_verified.json": ("records", 30),
    "data/bank_complaint_disclosures.json": ("records", 15),
    "data/canadian_source_registry.json": ("sources", 18),
    "data/obsi_annual_banking.json": ("rows", 5),
    "data/obsi_firm_complaints.json": ("records", 91),
    "data/ciro_enforcement_activity.json": ("firm_sanctions", 4),
    "data/ciro_named_enforcement.json": ("records", 5),
    "data/cafc_aggregates.json": ("rows", 1000),
    "data/osfi_institutions.json": ("records", 300),
    "data/canadian_regulatory_leads.json": ("leads", 0),
    "data/fintrac_penalties_official.json": ("records", 15),
}

def read(url):
    request=Request(url,headers={"User-Agent":"SignalNorth-PostDeploy-Health/1.0","Cache-Control":"no-cache"})
    with urlopen(request,timeout=20) as response:
        if response.status!=200:raise RuntimeError(f"{url}: HTTP {response.status}")
        return response.read()

def verify(base,sha):
    version="?audit="+(sha or "canadian-health")
    page=read(urljoin(base,"index.html")+version).decode("utf-8")
    if "__BUILD_SHA__" in page or (sha and sha not in page):
        raise AssertionError("Old build or unreplaced placeholder served")
    for marker in ['id="canadianSourceHub"','id="fintracOfficialPenalties"',
                   'id="bankDisclosure"','id="osfiRegisterPanel"','id="obsiHistoricalSeries"','id="obsiFirmRows"','id="ciroNamedRows"','id="provincialFeeds"']:
        if marker not in page:raise AssertionError("Missing section "+marker)
    scripts=sorted(set(re.findall(r'<script[^>]+src="\./([^"?]+)',page)))
    if len(scripts)<20:raise AssertionError(f"Only {len(scripts)} scripts referenced")
    for name in scripts:
        if len(read(urljoin(base,name)+version))<50:raise AssertionError(f"Missing or tiny script {name}")
    counts={}
    for name,(key,minimum) in REQUIRED.items():
        data=json.loads(read(urljoin(base,name)+version))
        rows=data.get(key)
        if not isinstance(rows,list) or len(rows)<minimum:
            raise AssertionError(f"{name} incomplete: expected at least {minimum} {key}")
        if name.endswith("osfi_institutions.json") and data.get("record_count")!=len(rows):
            raise AssertionError("OSFI count mismatch")
        if name.endswith("fintrac_penalties_official.json") and data.get("count")!=len(rows):
            raise AssertionError("FINTRAC count mismatch")
        counts[name]=len(rows)
    return {"scripts":len(scripts),"datasets":counts}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",default="https://khaled-agi.github.io/Signal-North/")
    ap.add_argument("--expected",default="")
    args=ap.parse_args()
    last=None
    for attempt in range(1,9):
        try:
            result=verify(args.base.rstrip("/")+"/",args.expected)
            print("LIVE SITE VERIFIED:",json.dumps(result,sort_keys=True))
            return
        except Exception as e:
            last=e
            print(f"Attempt {attempt}/8: {type(e).__name__}: {e}",flush=True)
            if attempt<8:time.sleep(10)
    raise SystemExit(f"Live site check failed: {last}")

if __name__=="__main__":main()
