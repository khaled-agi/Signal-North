#!/usr/bin/env python3
"""Build an evidence-aware institution intelligence graph and analyst review queue.

What this DOES: connects official regulatory actions, individually source-reviewed
reported incidents, and headline-only mentions by clearly stated entity/name cues.

What this does NOT do: prove fraud, infer that a bank caused customer losses,
conflate fines with fraud losses, or assert that similarly themed stories are the
same incident.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/"data"
sys.path.insert(0,str(Path(__file__).resolve().parent))
from entity_resolution import EntityMatcher, core_name, fold, looks_like_organisation  # noqa: E402

BANKS={
 "rbc":{"name":"Royal Bank of Canada","aliases":["Royal Bank of Canada","RBC"]},
 "td":{"name":"Toronto-Dominion Bank","aliases":["The Toronto-Dominion Bank","Toronto-Dominion Bank (The)","Toronto-Dominion Bank","TD Bank","TD Bank Group","TD Canada Trust","TD"]},
 "bmo":{"name":"Bank of Montreal","aliases":["Bank of Montreal","BMO","BMO Bank of Montreal"]},
 "scotiabank":{"name":"Scotiabank","aliases":["Bank of Nova Scotia (The)","Bank of Nova Scotia","The Bank of Nova Scotia","Scotiabank"]},
 "cibc":{"name":"Canadian Imperial Bank of Commerce","aliases":["Canadian Imperial Bank of Commerce","CIBC"]},
 "national-bank":{"name":"National Bank of Canada","aliases":["National Bank of Canada","National Bank"]},
 "desjardins":{"name":"Desjardins","aliases":["Desjardins Group","Desjardins","Fédération des caisses Desjardins du Québec"]},
 "tangerine":{"name":"Tangerine Bank","aliases":["Tangerine Bank","Tangerine"]},
 "simplii":{"name":"Simplii Financial","aliases":["Simplii Financial","Simplii"]},
 "laurentian":{"name":"Laurentian Bank of Canada","aliases":["Laurentian Bank of Canada","Laurentian Bank"]},
 "first-nations-bank":{"name":"First Nations Bank of Canada","aliases":["First Nations Bank of Canada"]},
 "versabank":{"name":"VersaBank","aliases":["VersaBank"]},
 # Brand labels and licensed entities remain distinct. In particular, the
 # Wealthsimple brand does not automatically equal any subsidiary legal entity.
 "wealthsimple-brand":{"name":"Wealthsimple","aliases":["Wealthsimple"]},
 "wealthsimple-investments":{"name":"Wealthsimple Investments Inc.","aliases":["Wealthsimple Investments Inc."]},
 "wealthsimple-digital-assets":{"name":"Wealthsimple Digital Assets Inc.","aliases":["Wealthsimple Digital Assets Inc."]},
 "shakepay":{"name":"Shakepay","aliases":["Shakepay","Shakepay Inc."]},
 "coinbase":{"name":"Coinbase","aliases":["Coinbase"]},
 "binance":{"name":"Binance","aliases":["Binance","Binance Holdings Limited"]},
 "kucoin":{"name":"KuCoin","aliases":["KuCoin"]},
 "cryptomus":{"name":"Cryptomus","aliases":["Cryptomus"]},
 "bclc":{"name":"BCLC","aliases":["BCLC","British Columbia Lottery Corporation"]},
 "atlantic-lottery":{"name":"Atlantic Lottery","aliases":["Atlantic Lottery","Atlantic Lottery Corporation"]},
 "cne-casino":{"name":"CNE Casino","aliases":["CNE Casino"]},
 # Canadian institutions frequently named in fraud reporting.
 "atb":{"name":"ATB Financial","aliases":["ATB Financial","Alberta Treasury Branches"]},
 "vancity":{"name":"Vancity","aliases":["Vancity","Vancouver City Savings Credit Union"]},
 "meridian-cu":{"name":"Meridian Credit Union","aliases":["Meridian Credit Union","Meridian Credit Union Limited"]},
 "eq-bank":{"name":"EQ Bank / Equitable Bank","aliases":["EQ Bank","Equitable Bank"]},
 "koho":{"name":"KOHO","aliases":["KOHO","KOHO Financial"]},
 "questrade":{"name":"Questrade","aliases":["Questrade","Questrade Inc."]},
 "interac":{"name":"Interac","aliases":["Interac","Interac Corp."]},
 # International banks, payment networks and crypto platforms. Brand-level
 # nodes: a US/UK regulated subsidiary keeps its own register identity.
 "bank-of-america":{"name":"Bank of America","aliases":["Bank of America","Bank of America, N.A."]},
 "jpmorgan":{"name":"JPMorgan Chase","aliases":["JPMorgan Chase","JPMorgan","JP Morgan","JPMorgan Chase Bank"]},
 "wells-fargo":{"name":"Wells Fargo","aliases":["Wells Fargo","Wells Fargo Bank"]},
 "citi":{"name":"Citigroup / Citibank","aliases":["Citigroup","Citibank"]},
 "hsbc":{"name":"HSBC","aliases":["HSBC","HSBC Bank"]},
 "barclays":{"name":"Barclays","aliases":["Barclays","Barclays Bank"]},
 "santander":{"name":"Santander","aliases":["Santander","Banco Santander","Santander Bank"]},
 "lloyds":{"name":"Lloyds Banking Group","aliases":["Lloyds Bank","Lloyds Banking Group"]},
 "natwest":{"name":"NatWest","aliases":["NatWest","NatWest Group"]},
 "standard-chartered":{"name":"Standard Chartered","aliases":["Standard Chartered"]},
 "ubs":{"name":"UBS","aliases":["UBS","UBS Group"]},
 "deutsche-bank":{"name":"Deutsche Bank","aliases":["Deutsche Bank","Deutsche Bank AG"]},
 "danske":{"name":"Danske Bank","aliases":["Danske Bank"]},
 "anz":{"name":"ANZ","aliases":["ANZ","ANZ Bank"]},
 "westpac":{"name":"Westpac","aliases":["Westpac"]},
 "commbank":{"name":"Commonwealth Bank of Australia","aliases":["Commonwealth Bank","Commonwealth Bank of Australia","CommBank"]},
 "revolut":{"name":"Revolut","aliases":["Revolut"]},
 "monzo":{"name":"Monzo","aliases":["Monzo","Monzo Bank"]},
 "paypal":{"name":"PayPal","aliases":["PayPal"]},
 "zelle":{"name":"Zelle","aliases":["Zelle"]},
 "western-union":{"name":"Western Union","aliases":["Western Union"]},
 "moneygram":{"name":"MoneyGram","aliases":["MoneyGram"]},
 "mastercard":{"name":"Mastercard","aliases":["Mastercard"]},
 "amex":{"name":"American Express","aliases":["American Express","Amex","American Express National Bank"]},
 "kraken":{"name":"Kraken","aliases":["Kraken","Payward"]},
 "okx":{"name":"OKX","aliases":["OKX"]},
 "bybit":{"name":"Bybit","aliases":["Bybit"]},
 "ftx":{"name":"FTX","aliases":["FTX","FTX Trading"]},
 "tether":{"name":"Tether","aliases":["Tether"]},

}
def normalize(x):
 # Accent-folded so "Ltée", "Québec" and "Fédération" compare consistently.
 return re.sub(r"^the ","",fold(x))

ALIASES={}
CORE_ALIASES={}
for key,b in BANKS.items():
 for alias in b["aliases"]:
  n=normalize(alias)
  # Normalize exact official names only; do NOT substring match e.g. RBC inside a family name.
  if n not in ALIASES or len(n)>len(ALIASES[n]):
   ALIASES[n]=key
  CORE_ALIASES.setdefault(core_name(alias),key)

def bank_key(name):
 n=normalize(name)
 if not n:return None
 if n in ALIASES:return ALIASES[n]
 # "VIP Realty Inc" (FINTRAC) and "VIP Realty Inc." / "VIP Realty Ltd" in other
 # feeds are one organisation name once legal-form suffixes are removed.
 core=core_name(name) or n
 if core in CORE_ALIASES:return CORE_ALIASES[core]
 # Unrecognized but explicitly named official institution (e.g. credit union).
 return "institution-"+hashlib.sha256(core.encode()).hexdigest()[:12]

def institution_name(key,raw):
 return BANKS[key]["name"] if key in BANKS else str(raw).strip()

def load(name,field):
 p=DATA/name
 if not p.exists():return []
 data=json.loads(p.read_text("utf-8"))
 return data.get(field,[])

def reference(kind,item):
 if kind=="enforcement":
  return {"kind":kind,"id":item.get("id"),"date":item.get("published_at"),
   "event_date":item.get("event_at"),"title":item.get("title"),
   "source_url":item.get("source_url"),"source":item.get("source"),
   "category":item.get("category"),"status":item.get("status"),
   "penalty_cad":item.get("penalty_cad"),"location":item.get("location"),
   "evidence":"regulator_published_action","role":"subject_of_enforcement"}
 if kind=="incident":
  return {"kind":kind,"id":item.get("id"),"date":item.get("reported_at"),
   "event_period":item.get("incident_period"),"title":item.get("title"),
   "source_url":item.get("source_url"),"source":item.get("source_name"),
   "category":item.get("fraud_type"),"amount_cad":item.get("amount_cad"),
   "amount_type":item.get("amount_type"),"recovery_status":item.get("recovery_status"),
   "location":item.get("location"),"evidence":item.get("evidence_status"),
   "role":item.get("institution_role")}
 return {"kind":"headline","id":item.get("id"),"date":item.get("published_at"),
  "title":item.get("title"),"source_url":item.get("url"),
  "source":item.get("publisher"),"category":item.get("category"),
  "source_count":item.get("number_of_article_links",1),
  "source_channels":item.get("source_channels",[]),
  "source_count":item.get("source_count",item.get("number_of_article_links",1)),
  "variation_count":item.get("variation_count",1),
  "headline_variations":item.get("headline_variations",[]),
  "amount_text":item.get("amount_strings_in_headline",[]),
  "location":item.get("map_location") or item.get("country"),"evidence":"unverified_headline",
  "role":"mentioned_in_headline_only"}

def regulator_lead_reference(item,source):
 return {"kind":"regulator_publication","id":item.get("id"),
  "date":item.get("publication_date") or item.get("first_observed_at"),
  "title":item.get("title"),"source_url":item.get("source_url") or item.get("url"),
  "source":item.get("regulator") or item.get("agency") or source,
  "category":item.get("category") or "Regulator publication",
  "location":item.get("country") or item.get("jurisdiction"),
  "evidence":item.get("evidence_tier") or item.get("source_kind") or "official_publication_lead",
  "role":"official_entity_name_in_regulator_publication"}

def global_enforcement_reference(item):
 return {"kind":"enforcement","id":item.get("id"),"date":item.get("published_at"),
  "event_date":item.get("event_at"),"title":item.get("title"),
  "source_url":item.get("source_url"),"source":item.get("regulator"),
  "category":item.get("category"),"status":item.get("status"),
  "penalty_cad":None,"penalty_amount":item.get("penalty_amount"),
  "penalty_currency":item.get("penalty_currency"),
  "location":item.get("country"),"evidence":"regulator_published_action",
  "role":"subject_of_enforcement"}

def strip_publisher(title,publisher):
 title=str(title or "");publisher=str(publisher or "").strip()
 if publisher and title.endswith(" - "+publisher):return title[:-(len(publisher)+3)]
 return title

# Themes are an analyst keyword routing aid, not factual findings against institutions.
THEMES={
 "Impersonation / social engineering":("impersonat","spoof","courier","social engineering","bank investigator","pretend","phishing"),
 "Investment and crypto scams":("investment","crypto","deepfake","trading scam","ponzi"),
 "Identity / account takeover":("identity","unauthorized","account takeover","credit line","card fraud","credential"),
 "Money laundering controls":("aml","anti money laundering","money laundering","blanchiment","fintrac","kyc"),
 "Payment fraud / BEC":("business email","invoice","payment redirection","wire transfer","e transfer","spear phishing"),
 "Consumer protection":("consumer protection","bank act","fcac","disclosure","fee rebate"),
 "Vulnerable customer harm":("senior","elder","retiree","vulnerab","88 year","fraud victim"),
}
def themes(item):
 text=" ".join(str(item.get(k) or "") for k in ("title","category","fraud_type")).casefold()
 return [name for name,words in THEMES.items() if any(w in text for w in words)]

def research_priority(article):
 # REVIEW PRIORITY only: no institutional or wrongdoing risk scoring.
 amount=bool(article.get("amount_strings_in_headline"))
 bank=bool(article.get("banks_mentioned_in_headline"))
 victim=bool(article.get("headline_case_candidate"))
 primary=any(x in str(article.get("publisher","")).lower() for x in ("rcmp","police","government"))
 score=(3 if bank else 0)+(2 if amount else 0)+(2 if victim else 0)+(2 if primary else 0)
 return min(score,9)

def generate():
 events=load("events.json","events")
 incidents=load("incidents.json","incidents")
 articles=load("reporting_groups.json","groups")
 if not articles:articles=load("article_index.json","articles")
 if not articles:articles=load("news.json","leads")+load("news_archive.json","leads")
 by_key={}
 def ensure(name):
  key=bank_key(name)
  if key is None:return None
  if key not in by_key:
   by_key[key]={"id":key,"name":institution_name(key,name),
    "aliases":BANKS.get(key,{}).get("aliases",[name]),
    "counts":{"enforcement":0,"incidents":0,"headlines":0,"regulator_publications":0},
    "evidence":[],"themes":[],"annual_penalties_cad":{},
    "recent_activity":None}
  by_key[key].setdefault("_names",set()).add(str(name).strip())
  return by_key[key]

 for event in events:
  entry=ensure(event.get("institution"))
  if not entry:continue
  entry["counts"]["enforcement"]+=1
  entry["evidence"].append(reference("enforcement",event))
  if event.get("penalty_cad") is not None and event.get("published_at"):
   year=str(event["published_at"])[:4]
   entry["annual_penalties_cad"][year]=round(entry["annual_penalties_cad"].get(year,0)+float(event["penalty_cad"]),2)
 for inc in incidents:
  if not inc.get("institution"):continue
  entry=ensure(inc["institution"])
  if not entry:continue
  entry["counts"]["incidents"]+=1
  entry["evidence"].append(reference("incident",inc))
 # Official institution context, FINTRAC penalty notices and bank complaints
 # are separate source-specific measures, not extra entries in regulator-event
 # or headline counters. No attempt is made to infer bank complaints from CAFC.
 osfi=load("osfi_institutions.json","records")
 bank_disclosures=load("bank_complaint_disclosures.json","records")
 fintrac=load("fintrac_penalties_official.json","records")
 fcac=[x for x in load("canadian_enforcement_verified.json","records") if x.get("agency")=="FCAC"]
 ciro_cases=load("ciro_named_enforcement.json","records")
 amf=load("amf_quebec_entities.json","records")
 obsi_sector=load("obsi_annual_banking.json","rows")
 obsi_firms=load("obsi_firm_complaints.json","records")
 fdic_banks=load("us_fdic_institutions.json","records")
 fdic_failures=load("us_fdic_failures.json","records")
 ncua_credit_unions=load("us_ncua_credit_unions.json","records")
 occ_actions=load("us_occ_enforcement_actions.json","records")
 ofac_entities=load("us_ofac_sdn_entities.json","records")
 sec_litigation=load("us_sec_litigation_releases.json","records")
 uk_sanctions=load("uk_sanctions_entities.json","records")
 for row in obsi_firms:
  entry=ensure(row.get("institution"))
  if entry:
   entry.setdefault("official_data",{}).setdefault("obsi_firm_complaints",[]).append(row)
 for row in osfi:
  fields=row.get("fields") or {}
  name=fields.get("Company Name","").strip()
  if not name:continue
  entry=ensure(name)
  entry.setdefault("official_data",{})["osfi"]={
   "name":name,"group":fields.get("FI Group Name"),
   "type":fields.get("FI Type Name"),"industry":fields.get("FI Industry Name"),
   "source_url":"https://open.canada.ca/data/en/dataset/b27ec3ef-7338-4e76-a6fd-128339a92df5"}
 for record in bank_disclosures:
  entry=ensure(record.get("institution"))
  if not entry:continue
  entry.setdefault("official_data",{}).setdefault("bank_disclosures",[]).append(record)
 for notice in fintrac:
  entry=ensure(notice.get("entity_name"))
  if not entry:continue
  entry.setdefault("official_data",{}).setdefault("fintrac_notices",[]).append({
   "record_id":notice.get("record_id"),"date":notice.get("published"),
   "penalty_cad":notice.get("penalty_cad"),"violation_count":notice.get("violation_count"),
   "status_summary":notice.get("status_summary"),"source_url":notice.get("source_url"),
   "source_kind":"official_FINTRAC_index"})
 for case in ciro_cases:
  entry=ensure(case.get("institution"))
  if not entry:continue
  entry.setdefault("official_data",{}).setdefault("ciro_concluded_cases",[]).append({
   "id":case.get("id"),"status":case.get("status"),"date":case.get("concluded_date"),
   "publication_date":case.get("publication_date"),"topic":case.get("topic"),
   "fine_cad":case.get("fine_cad"),"costs_cad":case.get("costs_cad"),
   "disgorgement_cad":case.get("disgorgement_cad"),"source_url":case.get("case_url"),
   "source_kind":case.get("source_kind"),
   "note":"Entity-specific disciplinary case; do not attribute to parent or affiliates."})
 for action in fcac:
  entry=ensure(action.get("name"))
  if not entry:continue
  entry.setdefault("official_data",{}).setdefault("fcac_notices",[]).append({
   "date":action.get("published"),"penalty_cad":action.get("penalty_cad"),
   "topic":action.get("topic"),"source_url":action.get("url"),
   "source_kind":"manually_transcribed_FCAC_index"})
 # Québec AMF institution register joins only on an exact recognized legal name.
 # The complete provincial directory remains browsable separately. Do not
 # guess that similarly named firms are the same regulated legal entity.
 for row in amf:
  fields=row.get("fields") or {}
  matches=[str(v).strip() for k,v in fields.items() if v and any(t in normalize(k) for t in ("nom","d nomination","d nomination sociale","raison sociale","institution","company name"))]
  for name in matches[:2]:
   key=bank_key(name)
   if key not in by_key:continue
   by_key[key].setdefault("official_data",{}).setdefault("amf_registrations",[]).append({
     "name":name,"source":"AMF Québec open data","source_url":"https://www.donneesquebec.ca/recherche/dataset/liste-des-institutions-financieres-et-agences-d-evaluation-du-credit",
     "entity_record_id":row.get("id")})
   break
 # United States: FDIC CERT is the stable institution identifier.
 # Never merge an American institution into a Canadian institution on name.
 # A resolution/failure event is not proof of fraud or poor AML controls.
 def ensure_fdic(row):
  cert=str(row.get("fdic_cert") or "").strip()
  if not cert.isdigit():return None
  key="us-fdic-"+cert
  if key not in by_key:
   name=str(row.get("institution") or "").strip()
   if not name:return None
   by_key[key]={
    "_names":{name},
    "id":key,"name":name+" (US · "+str(row.get("state") or "FDIC")+")",
    "legal_name":name,"jurisdiction":"US","country":"US",
    "aliases":[name,name+" FDIC "+cert],
    "counts":{"enforcement":0,"incidents":0,"headlines":0,"regulator_publications":0},
    "evidence":[],"themes":[],"annual_penalties_cad":{},
    "recent_activity":None,
   }
  return by_key[key]
 for bank in fdic_banks:
  entry=ensure_fdic(bank)
  if not entry:continue
  entry.setdefault("official_data",{})["fdic"]={
   "cert":bank.get("fdic_cert"),"legal_name":bank.get("institution"),
   "state":bank.get("state"),"city":bank.get("city"),
   "active":bank.get("active"),"fed_rssd":bank.get("fed_rssd"),
   "source_url":"https://banks.data.fdic.gov/bankfind-suite/",
   "source_kind":"official_FDIC_active_institution_register",
  }
 for failure in fdic_failures:
  entry=ensure_fdic(failure)
  if entry is None and failure.get("fdic_event_id"):
   # Legacy FDIC assistance can lack a current insured CERT.
   # Preserve it as a separate historical entity, never guess a name match.
   key="us-fdic-historical-"+str(failure["fdic_event_id"])
   if key not in by_key:
    rawname=str(failure.get("institution") or "FDIC historical record")
    by_key[key]={"id":key,"name":rawname+" (historical FDIC resolution)",
      "jurisdiction":"US","country":"US","aliases":[rawname],
      "counts":{"enforcement":0,"incidents":0,"headlines":0,"regulator_publications":0},
      "evidence":[],"themes":[],"annual_penalties_cad":{},
      "recent_activity":None}
   entry=by_key[key]
  if not entry:continue
  entry.setdefault("official_data",{}).setdefault("fdic_failure_events",[]).append({
   "date":failure.get("failure_date"),"resolution_type":failure.get("resolution_type"),
   "acquirer":failure.get("acquirer"),"state":failure.get("state"),
   "assets_thousands_usd":failure.get("assets_thousands_usd"),
   "deposits_thousands_usd":failure.get("deposits_thousands_usd"),
   "fdic_cert":failure.get("fdic_cert"),
   "source_url":"https://banks.data.fdic.gov/bankfind-suite/failures",
   "source_kind":"FDIC_bank_failure_or_assistance_event",
   "note":"Bank failure / assistance is NOT an enforcement or fraud allegation.",
  })
 # NCUA charter numbers are independent of FDIC certificates.
 # Two institutions with identical names must not be merged by string alone.
 for cu in ncua_credit_unions:
  charter=str(cu.get("ncua_charter") or "").strip()
  name=str(cu.get("institution") or "").strip()
  if not charter.isdigit() or not name:continue
  key="us-ncua-"+charter
  if key not in by_key:
   by_key[key]={
    "_names":{name},
    "id":key,"name":name+" (US credit union · "+str(cu.get("state") or "NCUA")+")",
    "legal_name":name,"jurisdiction":"US","country":"US",
    "aliases":[name,name+" NCUA "+charter],
    "counts":{"enforcement":0,"incidents":0,"headlines":0,"regulator_publications":0},
    "evidence":[],"themes":[],"annual_penalties_cad":{},
    "recent_activity":None,
   }
  by_key[key].setdefault("official_data",{})["ncua"]={
   "charter":charter,"legal_name":name,"city":cu.get("city"),"state":cu.get("state"),
   "cycle":cu.get("cycle"),"cu_type":cu.get("cu_type"),
   "source_url":"https://ncua.gov/analysis/credit-union-corporate-call-report-data/quarterly-data",
   "source_kind":"official_NCUA_quarterly_credit_union_roster",
  }
 # OCC national-bank charter is a separate legal identifier from FDIC CERT.
 # Without an explicit OCC charter -> FDIC CERT crosswalk, retain its own identity.
 # Individual-affiliated actions are not institutional wrongdoing.
 for notice in occ_actions:
  charter=str(notice.get("occ_charter") or "").strip()
  name=str(notice.get("institution") or "").strip()
  if not charter.isdigit() or not name:continue
  key="us-occ-"+charter
  if key not in by_key:
   by_key[key]={
    "_names":{name},
    "id":key,"name":name+" (OCC charter "+charter+")",
    "legal_name":name,"jurisdiction":"US","country":"US",
    "aliases":[name+" OCC "+charter],
    "counts":{"enforcement":0,"incidents":0,"headlines":0,"regulator_publications":0},
    "evidence":[],"themes":[],"annual_penalties_cad":{},"recent_activity":None,
   }
  entry=by_key[key]
  official=entry.setdefault("official_data",{})
  keyname="occ_individual_matters" if notice.get("subject_is_individual") else "occ_institution_actions"
  official.setdefault(keyname,[]).append({
    "id":notice.get("id"),"start_date":notice.get("start_date"),
    "case_type":notice.get("case_type"),"type_description":notice.get("action_description"),
    "amount_usd":notice.get("amount_usd"),"amount_raw":notice.get("amount_raw"),
    "docket":notice.get("docket"),"subject_matters":notice.get("subject_matters") or [],
    "individual_party":notice.get("individual_party"),"termination_date":notice.get("termination_date"),
    "source_url":notice.get("source_url"),"start_documents":notice.get("start_documents") or [],
    "source_kind":"OCC_official_case_record"})
  official["occ"]={"charter":charter,"legal_name":name,
    "source_url":"https://apps.occ.gov/EASearch",
    "note":"OCC charter identifier. No speculative FDIC CERT or Canadian entity merge."}

 # ------------------------------------------------------------------
 # Cross-source linking. Everything above is keyed by official identity;
 # below, news headlines and regulator publications are connected to those
 # identities when they name an organisation exactly as an official source
 # lists it. A name match is a research lead, never a finding.
 # ------------------------------------------------------------------
 global_events=load("global_enforcement.json","events")
 global_linked=0
 for ev in global_events:
  name=ev.get("institution")
  if not looks_like_organisation(name):continue  # individuals are never indexed
  entry=ensure(name)
  if not entry:continue
  entry.setdefault("jurisdiction",ev.get("country_code"))
  entry["counts"]["enforcement"]+=1
  entry["evidence"].append(global_enforcement_reference(ev))
  global_linked+=1

 sanctions={};pending={};pending_names={}
 def designate(primary,names,payload):
  key=bank_key(primary)
  if not key:return
  sanctions.setdefault(key,[]).append(payload)
  pending.setdefault(key,str(primary).strip())
  pending_names.setdefault(key,set()).update(n for n in names if n)
 uk_groups={}
 for row in uk_sanctions:
  uid=row.get("uk_unique_id") or row.get("name")
  uk_groups.setdefault(uid,[]).append(row)
 for uid,rows in uk_groups.items():
  primary=next((r for r in rows if str(r.get("name_type","")).casefold().startswith("primary")),rows[0])
  designate(primary.get("name"),[r.get("name") for r in rows],{
   "list":"UK FCDO sanctions list","id":uid,"regime":primary.get("regime"),
   "date_designated":primary.get("date_designated"),"measures":primary.get("sanctions_imposed"),
   "source_url":primary.get("source_url") or "https://www.gov.uk/government/publications/the-uk-sanctions-list"})
 for row in ofac_entities:
  designate(row.get("name"),[row.get("name")],{
   "list":"US OFAC SDN list","id":row.get("ofac_ent_num"),
   "regime":", ".join(row.get("sanctions_programs") or []) or None,
   "date_designated":None,"measures":"OFAC SDN designation",
   "source_url":row.get("source_url") or "https://ofac.treasury.gov/sanctions-list-service"})

 matcher=EntityMatcher()
 for key,b in BANKS.items():
  for alias in b["aliases"]:matcher.add(key,alias,curated=True)
 for key,entry in by_key.items():
  if key in BANKS:continue
  # US register names ("West Shore Bank") are matched in full only: shortened
  # forms of small-bank names are usually just place names.
  us_register=key.startswith("us-")
  for n in entry.get("_names",()):
   if looks_like_organisation(n):matcher.add(key,n,allow_variant=not us_register)
 for key,names in pending_names.items():
  for n in names:matcher.add(key,n)
 matcher.compile()

 def resolve(key):
  if key in by_key:return by_key[key]
  if key in pending:return ensure(pending[key])
  if key in BANKS:return ensure(BANKS[key]["name"])
  return None

 world=load("world_reporting.json","leads")
 reg_leads=load("global_regulator_publications.json","leads")
 official_hits={}
 article_entities={}
 stats={"headlines_scanned":0,"headlines_linked":0,"links_from_curated_extraction":0,
        "links_from_official_name_match":0,"regulator_publications_scanned":0,
        "regulator_publications_linked":0,"global_enforcement_linked":global_linked}
 def link_headline(art,channel=None):
  stats["headlines_scanned"]+=1
  found={}
  for name in (art.get("banks_mentioned_in_headline") or [])+(art.get("organizations_mentioned_in_headline") or []):
   key=bank_key(name)
   if key:found.setdefault(key,("mentioned_in_headline_only",None,name))
  for hit in matcher.find(strip_publisher(art.get("title"),art.get("publisher"))):
   if hit["key"] not in found:
    found[hit["key"]]=("official_entity_name_in_headline",hit["basis"],hit["phrase"])
  linked=False
  for key,(role,basis,phrase) in sorted(found.items()):
   entry=resolve(key) if role!="mentioned_in_headline_only" else ensure(BANKS[key]["name"] if key in BANKS else phrase)
   if not entry:continue
   ref=reference("headline",art)
   if channel and not ref.get("source_channels"):ref["source_channels"]=[channel]
   if role!="mentioned_in_headline_only":
    ref["role"]=role;ref["match_basis"]=basis;ref["matched_name"]=phrase
    stats["links_from_official_name_match"]+=1
    official_hits.setdefault(art.get("id"),[]).append(entry["name"])
   else:
    stats["links_from_curated_extraction"]+=1
   entry["counts"]["headlines"]+=1  # One grouped report; not one incident or source
   if art.get("id"):article_entities.setdefault(art["id"],set()).add(entry["id"])
   entry["evidence"].append(ref)
   linked=True
  stats["headlines_linked"]+=linked
 for art in articles:link_headline(art)
 for art in world:link_headline(art,"worldwide news search")
 for source,items in (("Regulator website",reg_leads),("SEC litigation release",sec_litigation)):
  for item in items:
   stats["regulator_publications_scanned"]+=1
   hits=matcher.find(item.get("title"))
   for hit in hits:
    entry=resolve(hit["key"])
    if not entry:continue
    ref=regulator_lead_reference(item,source)
    ref["match_basis"]=hit["basis"];ref["matched_name"]=hit["phrase"]
    entry["counts"]["regulator_publications"]+=1
    entry["evidence"].append(ref)
   stats["regulator_publications_linked"]+=bool(hits)
 # Sanctions designations attach to any node whose official name resolves to
 # the same organisation key. Unlinked designations stay in the list views.
 for entry in by_key.values():
  seen=set()
  for n in entry.get("_names",()):
   for d in sanctions.get(bank_key(n),[]):
    ident=(d["list"],d["id"])
    if ident in seen:continue
    seen.add(ident)
    entry.setdefault("official_data",{}).setdefault("sanctions_designations",[]).append(d)
 stats["ambiguous_names_skipped"]=len(matcher.ambiguous)
 for entry in by_key.values():
  official=entry.setdefault("official_data",{})
  official["counts"]={"fintrac_public_notices":len(official.get("fintrac_notices",[])),
     "fcac_index_notices":len(official.get("fcac_notices",[])),
     "bank_disclosure_years":len(official.get("bank_disclosures",[])),
     "obsi_firm_years":len(official.get("obsi_firm_complaints",[])),
     "ciro_concluded_cases":len(official.get("ciro_concluded_cases",[])),
     "fdic_failures":len(official.get("fdic_failure_events",[])),
     "occ_institution_actions":len(official.get("occ_institution_actions",[])),
     "occ_individual_matters":len(official.get("occ_individual_matters",[])),
     "sanctions_designations":len(official.get("sanctions_designations",[]))}
  if official.get("bank_disclosures"):
   official["bank_disclosures"].sort(key=lambda x:x.get("year",0),reverse=True)
  if official.get("fintrac_notices"):
   official["fintrac_notices"].sort(key=lambda x:x.get("date") or "",reverse=True)
 for entry in by_key.values():
  entry["evidence"].sort(key=lambda e:str(e.get("date") or ""),reverse=True)
  entry["recent_activity"]=entry["evidence"][0].get("date") if entry["evidence"] else None
  theme_counter=Counter()
  for obj in entry["evidence"]:
   for theme in themes(obj):theme_counter[theme]+=1
  entry["themes"]=[{"name":theme,"matching_records":count,"interpretation":"shared keyword, not established causation"} for theme,count in theme_counter.most_common(8)]
  # Keep all source-linked official events + reviewed cases, and up to 120
  # headline mentions per institution. Full article archive remains searchable.
  limited=[];news_count=0
  for rec in entry["evidence"]:
   if rec["kind"]=="headline":
    news_count+=1
    if news_count>120:continue
   limited.append(rec)
  entry["evidence"]=limited
  entry["evidence_count_shown"]=len(limited)
  entry.pop("_names",None)
 def source_types(e):
  kinds={k for k,v in e["counts"].items() if v}
  kinds|={k for k,v in e.get("official_data",{}).items() if k!="counts" and v}
  return kinds
 stats["institutions_with_2plus_source_types"]=sum(len(source_types(e))>=2 for e in by_key.values())
 stats["institutions_with_news_and_official_record"]=sum(
  bool(e["counts"]["headlines"]) and bool(source_types(e)-{"headlines"}) for e in by_key.values())
 ranked=sorted(by_key.values(),key=lambda e:(e["counts"]["enforcement"]+e["counts"]["incidents"],e["counts"]["headlines"]),reverse=True)
 DATA.mkdir(parents=True,exist_ok=True)
 graph={
  "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "methodology":"Institution names are canonically grouped using explicit aliases and legal-suffix-insensitive official names. Headlines and regulator publications link to an organisation only when they contain its full official name (or curated alias) and that name is unambiguous; individuals are never name-matched. Headline entries are conservative reporting groups, not distinct or independently verified fraud incidents; multiple publisher headlines are retained under each group. An institution mention is not proof of wrongdoing.",
  "source_counts":{"enforcement":len(events),"reviewed_incidents":len(incidents),"unverified_report_groups":len(articles),
    "osfi_institution_rows":len(osfi),"fintrac_index_notices":len(fintrac),
    "bank_disclosure_records":len(bank_disclosures),"fcac_manual_sample":len(fcac),
    "obsi_banking_years":len(obsi_sector),"obsi_firm_records":len(obsi_firms),"ciro_confirmed_cases":len(ciro_cases),"amf_quebec_entity_rows":len(amf),
    "us_fdic_active_entities":len(fdic_banks),"us_fdic_failure_events":len(fdic_failures),
    "us_ncua_credit_union_entities":len(ncua_credit_unions),
    "us_occ_enforcement_actions":len(occ_actions),"us_ofac_sdn_entity_designations":len(ofac_entities),
    "us_sec_litigation_publications":len(sec_litigation),"uk_sanctions_entity_designations":len(uk_sanctions),
    "global_enforcement_events":len(global_events),"world_reporting_headlines":len(world),
    "regulator_publication_leads":len(reg_leads)},
  "linking":stats,
  "sector_context":{"obsi_banking":obsi_sector,"note":"OBSI annual sector totals must not be attributed to individual institutions."},
  "institutions":ranked
 }
 (DATA/"institution_intelligence.json").write_text(json.dumps(graph,ensure_ascii=False,separators=(",",":"))+"\n","utf-8")

 # Entity ids per reporting group, consumed by build_related_reporting.py so
 # stories naming the same organisation can be suggested for comparison.
 (DATA/"headline_entities.json").write_text(json.dumps({
  "generated_at":graph["generated_at"],
  "methodology":"Organisation ids whose official name or curated alias appears in the headline. Name presence only.",
  "names":{k:by_key[k]["name"] for ids in article_entities.values() for k in ids if k in by_key},
  "articles":{k:sorted(v) for k,v in article_entities.items()}},ensure_ascii=False,separators=(",",":"))+"\n","utf-8")
 queue=[]
 for article in articles:
  priority=research_priority(article)
  named=official_hits.get(article.get("id"),[])
  if named and not article.get("banks_mentioned_in_headline"):priority=min(9,priority+3)
  if priority<2:continue
  queue.append({
   "article_id":article.get("id"),
   "headline":article.get("title"),"date":article.get("published_at"),
   "source_url":article.get("url"),"publisher":article.get("publisher"),
   "priority":priority,"priority_basis":[x for x,yes in (
    ("named bank in headline",bool(article.get("banks_mentioned_in_headline"))),
    ("organisation named in official records",bool(named)),
    ("currency or amount in headline",bool(article.get("amount_strings_in_headline"))),
    ("possible victim story",bool(article.get("headline_case_candidate")))) if yes],
   "banks":article.get("banks_mentioned_in_headline",[]),
   "official_entities":named,
   "amount_text":article.get("amount_strings_in_headline",[]),
   "review_status":"unreviewed_headline_only",
   "next_step":"Open original reporting, confirm event vs publication date, institution role, victim loss vs exposure vs recovery, and any corroborating police/regulator evidence."
  })
 queue.sort(key=lambda x:(-x["priority"],str(x.get("date") or "")),reverse=False)
 queue.sort(key=lambda x:x.get("date") or "",reverse=True)
 queue.sort(key=lambda x:x["priority"],reverse=True)
 (DATA/"review_queue.json").write_text(json.dumps({
  "generated_at":graph["generated_at"],
  "methodology":"Priority scores determine what an analyst reviews first, NOT bank risk or culpability. These are not verified incidents.",
  "total_candidates":len(queue),
  "items":queue[:250]
 },ensure_ascii=False,indent=2)+"\n","utf-8")
 print(json.dumps({"institutions":len(ranked),"official_records":len(events),
                   "reviewed_incidents":len(incidents),"headline_leads":len(articles),
                   "review_candidates":len(queue),"linking":stats,"sample":ranked[:5] and
                    [{"institution":x["name"],**x["counts"]} for x in ranked[:5]]},indent=2))

if __name__=="__main__":
 generate()
