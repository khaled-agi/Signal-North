#!/usr/bin/env python3
"""Longitudinal fraud theme *coverage*, not underlying incident prevalence.

Counts deduplicated headlines from independently indexed reports by publication
year. Multiple overlapping themes are supported. No claim that story frequency
measures fraud incidence or that a platform mentioned was at fault.
"""
from __future__ import annotations
import json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/"data"
TAXONOMY={
 "Bank impersonation & phishing":["impersonat","spoof","phishing","fake bank","bank fraud department","faux conseiller","hameçonnage","vishing"],
 "Account takeover & identity":["account takeover","unauthoriz","identity theft","identity fraud","stolen identity","credit line","compromised account","fraude d.identit","vol d.identit"],
 "Investment & crypto scams":["crypto","bitcoin","cryptomonnaie","investment scam","investment fraud","investment scheme","fake investment","ponzi","trading platform","pig butchering","placement frauduleux"],
 "Romance & relationship scams":["romance scam","romance fraud","dating scam","love scam","romantique","sentimental","relation amoureuse"],
 "Payment fraud & e-transfer":["e-transfer","etransfer","wire fraud","wire transfer","payment diversion","invoice fraud","business email compromise","bec scam","interac","interception"],
 "Jobs, rentals & marketplace":["job scam","job fraud","employment scam","fake job","rental scam","apartment scam","marketplace scam","facebook marketplace","task scam","emploi frauduleux"],
 "Seniors & vulnerable victims":["senior","elder","retiree","vulnerable","pensioner","aîné","personne âgée"],
 "Money mules & laundering":["money mule","money laundering","blanchiment","mule account","illicit funds","proceeds of crime","aml program","anti-money laundering"],
 "Gambling, gaming & casino":["casino","online betting","gambling","igaming","sports betting","lottery","lotteries","jeux d.argent","gambling site"],
 "Digital fraud & cybercrime":["ransomware","cybercrime","cyberattack","data breach","sim swap","deepfake","ai-generated","hackers","hacked","rançongiciel"],
 "Recovery & follow-on scams":["recovery scam","recovery fraud","recover lost funds","recovery agent","fund recovery","refund scam"],
 "Fraud investigations & enforcement":["fintrac","ciro","agco","securities commission","enforcement action","charged with fraud","arrested for fraud","anti-fraud centre"],
}
ENTITY_TERMS={
 "Wealthsimple":r"(?<!\w)wealthsimple(?!\w)",
 "TD":r"(?<!\w)(?:td bank|toronto.dominion|td canada trust)(?!\w)",
 "RBC":r"(?<!\w)(?:rbc|royal bank of canada)(?!\w)",
 "Scotiabank":r"(?<!\w)(?:scotiabank|bank of nova scotia)(?!\w)",
 "CIBC":r"(?<!\w)cibc(?!\w)",
 "BMO":r"(?<!\w)(?:bmo|bank of montreal)(?!\w)",
 "Shakepay":r"(?<!\w)shakepay(?!\w)",
 "Coinbase":r"(?<!\w)coinbase(?!\w)",
 "Binance":r"(?<!\w)binance(?!\w)",
 "KuCoin":r"(?<!\w)kucoin(?!\w)",
 "Cryptomus":r"(?<!\w)cryptomus(?!\w)",
 "CNE Casino":r"(?<!\w)cne casino(?!\w)",
 "BCLC":r"(?<!\w)(?:bclc|british columbia lottery)(?!\w)",
}
def match_themes(title):
 t=(title or "").casefold()
 return [theme for theme,terms in TAXONOMY.items() if any(term.casefold() in t for term in terms)]
def classify_articles(articles,years=range(2020,2027)):
 years=[str(y) for y in years]
 out={k:{"year_counts":{y:0 for y in years},"examples":[],"publisher_count":Counter(),"matched_total":0} for k in TAXONOMY}
 by_year=Counter()
 articles_sorted=sorted(articles,key=lambda x:str(x.get("published_at") or ""),reverse=True)
 entities=defaultdict(Counter)
 for a in articles_sorted:
  year=str(a.get("published_at") or "")[:4]
  if year not in years:continue
  title=a.get("title") or ""
  by_year[year]+=1
  for name,pattern in ENTITY_TERMS.items():
   if re.search(pattern,title,re.I):entities[name][year]+=1
  for theme in match_themes(title):
   o=out[theme]
   o["year_counts"][year]+=1
   o["matched_total"]+=1
   o["publisher_count"][a.get("publisher") or "Unknown"]+=1
   if len(o["examples"])<24:
    o["examples"].append({
     "id":a.get("id"),"title":title,"date":a.get("published_at"),
     "publisher":a.get("publisher"),"url":a.get("url"),
     "geography":a.get("map_location"),
     "source_channels":a.get("source_channels",[]),
    })
 themes=[]
 for k,x in out.items():
  themes.append({
   "name":k,"year_counts":x["year_counts"],"total_headlines":x["matched_total"],
   "publisher_count":len(x["publisher_count"]),
   "examples":x["examples"],
  })
 themes.sort(key=lambda x:x["total_headlines"],reverse=True)
 return {
  "years":years,"articles_by_year":{y:by_year[y] for y in years},
  "themes":themes,
  "institution_headline_mentions":[{"name":name,"counts":{y:entity_counts[y] for y in years}} for name,entity_counts in sorted(entities.items())],
 }
def main():
 index=json.loads((DATA/"article_index.json").read_text("utf-8"))
 data=classify_articles(index.get("articles",[]))
 data.update({
  "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "articles_analyzed":len(index.get("articles",[])),
  "methodology":"MULTI-LABEL keyword classification of unique article TITLES by publication year; multiple theme counts can arise from one headline. Year-to-year article counts reflect discovery methods, changing news coverage, and archived source availability, NOT measured changes in fraud incidence. Bank/platform mentions are not accusations and never counted as confirmed enforcement.",
  "scope":"Canadian financial-crime news discovery",
  "data_quality":"Headlines only; no full-article automated fact checking. Counts can change as the archive expands.",
 })
 (DATA/"theme_trends.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n","utf-8")
 print(json.dumps({"articles":data["articles_analyzed"],"themes":len(data["themes"]),"years":data["articles_by_year"]}))
if __name__=="__main__":
 main()
