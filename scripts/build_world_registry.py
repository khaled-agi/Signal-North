#!/usr/bin/env python3
"""Primary regulator jurisdictions for an extensible worldwide intelligence map.

Jurisdiction centroids are *not* incident coordinates. A country without official
collected actions gets a discoverable country record, never a fabricated marker.
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pycountry
from countryinfo import CountryInfo

DATA=Path(__file__).resolve().parents[1]/"data"
CENTROID_OVERRIDES={
 "US":[39.8,-98.6],"CA":[57,-101],"GB":[54,-2.7],"AU":[-25,134],
 "FR":[46.6,2.2],"DE":[51.2,10.4],"JP":[36.2,138.2],
 "IN":[22.6,79],"AE":[24,54],"HK":[22.4,114.1],
 "SG":[1.35,103.8],"KR":[36,127.8],"XK":[42.6,20.9],
}
def read(path,key):
 p=DATA/path
 if not p.exists():return []
 return json.loads(p.read_text("utf-8")).get(key,[])
def build():
 info={}
 for x in CountryInfo().all().values():
  iso=x.get("ISO") or {}
  code=iso.get("alpha2")
  if code and len(code)==2:info[code]=x
 global_events=read("global_enforcement.json","events")
 countries=[{"code":"CA","name":"Canada","map_latitude":57,"map_longitude":-101,
   "enforcement_count":len(read("events.json","events")),"coverage":"active",
   "agency_count":2,"location_role":"regulatory_jurisdiction_centroid"}]
 count=Counter(x.get("country_code") for x in global_events)
 regulators={}
 for e in global_events:
  regulators.setdefault(e.get("country_code"),set()).add(e.get("regulator"))
 for c in pycountry.countries:
  if c.alpha_2=="CA":continue
  geo=info.get(c.alpha_2,{}).get("latlng") or CENTROID_OVERRIDES.get(c.alpha_2)
  if not geo or len(geo)<2:geo=None
  countries.append({
   "code":c.alpha_2,"name":getattr(c,"common_name",c.name),
   "map_latitude":round(float(geo[0]),4) if geo else None,
   "map_longitude":round(float(geo[1]),4) if geo else None,
   "enforcement_count":count.get(c.alpha_2,0),
   "agency_count":len(regulators.get(c.alpha_2,[])),
   "coverage":"active" if count.get(c.alpha_2,0) else "not_ingested",
   "location_role":"regulatory_jurisdiction_centroid",
  })
 countries.sort(key=lambda x:x["name"])
 out={
  "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "jurisdictions":countries,
  "coverage_note":"ISO-3166 country and territory catalogue, not an assertion that all countries are monitored. Pins appear only for actual ingested official-source records. Country location is a representative centroid of the publishing enforcement jurisdiction, never an incident site.",
  "total_jurisdictions":len(countries),
  "active_jurisdictions":sum(x["coverage"]=="active" for x in countries),
 }
 (DATA/"world_jurisdictions.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n","utf-8")
 print(json.dumps({"jurisdictions":out["total_jurisdictions"],"active":out["active_jurisdictions"]}))
if __name__=="__main__":
 build()
