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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/"data"

BANKS={
 "rbc":{"name":"Royal Bank of Canada","aliases":["Royal Bank of Canada","RBC"]},
 "td":{"name":"Toronto-Dominion Bank","aliases":["The Toronto-Dominion Bank","Toronto-Dominion Bank","TD Bank","TD Canada Trust","TD"]},
 "bmo":{"name":"Bank of Montreal","aliases":["Bank of Montreal","BMO","BMO Bank of Montreal"]},
 "scotiabank":{"name":"Scotiabank","aliases":["Bank of Nova Scotia","The Bank of Nova Scotia","Scotiabank"]},
 "cibc":{"name":"Canadian Imperial Bank of Commerce","aliases":["Canadian Imperial Bank of Commerce","CIBC"]},
 "national-bank":{"name":"National Bank of Canada","aliases":["National Bank of Canada","National Bank"]},
 "desjardins":{"name":"Desjardins","aliases":["Desjardins Group","Desjardins","Fédération des caisses Desjardins du Québec"]},
 "tangerine":{"name":"Tangerine Bank","aliases":["Tangerine Bank","Tangerine"]},
 "simplii":{"name":"Simplii Financial","aliases":["Simplii Financial","Simplii"]},
 "laurentian":{"name":"Laurentian Bank of Canada","aliases":["Laurentian Bank of Canada","Laurentian Bank"]},
 "first-nations-bank":{"name":"First Nations Bank of Canada","aliases":["First Nations Bank of Canada"]},
 "versabank":{"name":"VersaBank","aliases":["VersaBank"]},
}
def normalize(x):
 s=re.sub(r"[^a-z0-9]+"," ",str(x or "").casefold()).strip()
 return re.sub(r"^the ","",s)

ALIASES={}
for key,b in BANKS.items():
 for alias in b["aliases"]:
  n=normalize(alias)
  # Normalize exact official names only; do NOT substring match e.g. RBC inside a family name.
  if n not in ALIASES or len(n)>len(ALIASES[n]):
   ALIASES[n]=key

def bank_key(name):
 n=normalize(name)
 if not n:return None
 if n in ALIASES:return ALIASES[n]
 # Unrecognized but explicitly named official institution (e.g. credit union).
 return "institution-"+hashlib.sha256(n.encode()).hexdigest()[:12]

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
  "amount_text":item.get("amount_strings_in_headline",[]),
  "location":item.get("map_location"),"evidence":"unverified_headline",
  "role":"mentioned_in_headline_only"}

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
 articles=load("article_index.json","articles")
 if not articles:articles=load("news.json","leads")+load("news_archive.json","leads")
 by_key={}
 def ensure(name):
  key=bank_key(name)
  if key is None:return None
  if key not in by_key:
   by_key[key]={"id":key,"name":institution_name(key,name),
    "aliases":BANKS.get(key,{}).get("aliases",[name]),
    "counts":{"enforcement":0,"incidents":0,"headlines":0},
    "evidence":[],"themes":[],"annual_penalties_cad":{},
    "recent_activity":None}
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
 for art in articles:
  # Only explicit banks_mentioned_in_headline qualifies for a tentative link.
  keys=set()
  for name in art.get("banks_mentioned_in_headline",[]):
   key=bank_key(name)
   if key:keys.add(key)
  for key in sorted(keys):
   name=BANKS[key]["name"] if key in BANKS else next((a for a in art.get("banks_mentioned_in_headline",[]) if bank_key(a)==key),"")
   entry=ensure(name)
   if not entry:continue
   entry["counts"]["headlines"]+=1
   entry["evidence"].append(reference("headline",art))
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
 ranked=sorted(by_key.values(),key=lambda e:(e["counts"]["enforcement"]+e["counts"]["incidents"],e["counts"]["headlines"]),reverse=True)
 DATA.mkdir(parents=True,exist_ok=True)
 graph={
  "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "methodology":"Exact official institution names are canonically grouped by listed aliases. Articles linked to banks only when the bank is explicitly named in a headline. This is an evidence research aid, not proof of wrongdoing.",
  "source_counts":{"enforcement":len(events),"reviewed_incidents":len(incidents),"unverified_articles":len(articles)},
  "institutions":ranked
 }
 (DATA/"institution_intelligence.json").write_text(json.dumps(graph,ensure_ascii=False,indent=2)+"\n","utf-8")

 queue=[]
 for article in articles:
  priority=research_priority(article)
  if priority<2:continue
  queue.append({
   "article_id":article.get("id"),
   "headline":article.get("title"),"date":article.get("published_at"),
   "source_url":article.get("url"),"publisher":article.get("publisher"),
   "priority":priority,"priority_basis":[x for x,yes in (
    ("named bank in headline",bool(article.get("banks_mentioned_in_headline"))),
    ("currency or amount in headline",bool(article.get("amount_strings_in_headline"))),
    ("possible victim story",bool(article.get("headline_case_candidate")))) if yes],
   "banks":article.get("banks_mentioned_in_headline",[]),
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
                   "review_candidates":len(queue),"sample":ranked[:5] and
                    [{"institution":x["name"],**x["counts"]} for x in ranked[:5]]},indent=2))

if __name__=="__main__":
 generate()
