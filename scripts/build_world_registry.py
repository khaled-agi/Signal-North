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
try:
 from .world_country_lenses import country_profile, research_jurisdictions
except ImportError:
 from world_country_lenses import country_profile, research_jurisdictions

DATA=Path(__file__).resolve().parents[1]/"data"
CENTROID_OVERRIDES={
 "US":[39.8,-98.6],"CA":[57,-101],"GB":[54,-2.7],"AU":[-25,134],
 "FR":[46.6,2.2],"DE":[51.2,10.4],"JP":[36.2,138.2],
 "IN":[22.6,79],"AE":[24,54],"HK":[22.4,114.1],
 "SG":[1.35,103.8],"KR":[36,127.8],"XK":[42.6,20.9],
 # Approximate RESEARCH MAP browsing points, never alleged incident locations.
 # Geographically dispersed Antarctica and US Minor Outlying Islands intentionally
 # remain without a misleading single representative marker.
 "AD":[42.5,1.52],"BQ":[12.2,-68.3],"BV":[-54.42,3.38],
 "CW":[12.17,-68.99],"VA":[41.903,12.453],"ME":[42.7,19.25],
 "MM":[21.9,95.9],"PS":[31.7,34.95],"BL":[17.9,-62.83],
 "MF":[18.08,-63.07],"SX":[18.04,-63.05],"TC":[21.8,-71.8],
 "VG":[18.42,-64.63],"VI":[18.33,-64.92],"AX":[60.15,19.94],
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
 world_reports=read("world_reporting.json","leads")
 world_status={}
 status_path=DATA/"world_reporting_status.json"
 if status_path.exists():
  world_status=json.loads(status_path.read_text("utf-8")).get("countries",{})
 reporting_counts=Counter(x.get("country_code") for x in world_reports)
 def details(code, country):
  profile=country_profile(country)
  attempt=world_status.get(code,{})
  return {"world_reporting_count":reporting_counts.get(code,0),
    "world_reporting_state":attempt.get("state","not_attempted"),
    "world_reporting_last_attempt_at":attempt.get("attempted_at"),
    "catalogue_type":profile["catalogue_type"],
    "language_strategy":profile["language_strategy"],
    "local_language":profile["local_language"],
    "agency_directory":profile["agency_directory"],
    "country_basis":"country_search_market_not_verified_event_location"}
 canada=pycountry.countries.get(alpha_2="CA")
 countries=[{"code":"CA","name":"Canada","map_latitude":57,"map_longitude":-101,
   "enforcement_count":len(read("events.json","events")),"coverage":"active",
   "agency_count":2,"location_role":"regulatory_jurisdiction_centroid",
   **details("CA",canada)}]
 count=Counter(x.get("country_code") for x in global_events)
 regulators={}
 for e in global_events:
  regulators.setdefault(e.get("country_code"),set()).add(e.get("regulator"))
 for c in research_jurisdictions():
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
   **details(c.alpha_2,c),
  })
 countries.sort(key=lambda x:x["name"])
 out={
  "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "jurisdictions":countries,
  "coverage_note":"ISO-3166 country and territory catalogue plus labeled non-ISO research jurisdictions (e.g. Kosovo XK). Official enforcement, country-language news discovery, and unattempted markets are separate coverage levels. A country discovery result is a search-market label only, NOT a geolocated alleged crime. Pins use country centroids solely for geographic browsing, never incident coordinates.",
  "markets_with_recent_reporting":sum(bool(x.get("world_reporting_count")) for x in countries),
  "markets_attempted":sum(x.get("world_reporting_state")!="not_attempted" for x in countries),
  "iso_jurisdictions":len(pycountry.countries),
  "non_iso_research_jurisdictions":sum(x.get("catalogue_type")=="non_iso_user_assigned" for x in countries),
  "total_jurisdictions":len(countries),
  "active_jurisdictions":sum(x["coverage"]=="active" for x in countries),
 }
 (DATA/"world_jurisdictions.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n","utf-8")
 print(json.dumps({"jurisdictions":out["total_jurisdictions"],"active":out["active_jurisdictions"]}))
if __name__=="__main__":
 build()
