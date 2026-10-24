#!/usr/bin/env python3
"""Build a canonical, source-traceable metadata index of Canadian fraud coverage.

Merge Google News, RCMP, GDELT and historical records while retaining original
URLs. A merged *article headline* is NOT a confirmed single fraud incident.
"""
from __future__ import annotations
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DATA=Path(__file__).resolve().parents[1]/"data"
OUTPUT=DATA/"article_index.json"
INPUTS=[("news.json","recent"),("news_archive.json","historical")]
SUFFIX=re.compile(r"\s+[-–—|]\s+(?:CBC(?: News)?|CTV(?: News)?|Global News|"
    r"CityNews|Yahoo (?:Finance|News)|BNN Bloomberg|Toronto Star|"
    r"The Globe and Mail|National Post|La Presse|Radio-Canada|RCMP|"
    r"Financial Post|The Canadian Press)\s*$",re.I)

def norm_title(s):
    s=SUFFIX.sub("",str(s or ""))
    s=unicodedata.normalize("NFKD",s)
    s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+"," ",s.casefold()).strip()

def score_source(x):
    url=x.get("url","")
    src=x.get("discovery_source","")
    return (3 if src=="rcmp_official_rss" else 2 if src=="gdelt_doc_2" else 1, 0 if "news.google.com" in url else 1)

def group_key(item):
    title=norm_title(item.get("title"))
    month=str(item.get("published_at") or "")[:7]
    if len(title)<45:
        publisher=item.get("publisher","")
        return month+"|"+title+"|"+publisher.casefold()
    return month+"|"+title

def build():
    gathered=[]
    for name,channel in INPUTS:
        p=DATA/name
        if p.exists():
            payload=json.loads(p.read_text("utf-8"))
            gathered += [(dict(item),channel) for item in payload.get("leads",[])]
    groups={}
    for item,channel in gathered:
        if not item.get("title") or not item.get("url"):
            continue
        key=group_key(item)
        groups.setdefault(key,[]).append((item,channel))
    articles=[]
    for key,items in groups.items():
        best=max((item for item,_ in items),key=score_source)
        out=dict(best)
        links={}
        for item,channel in items:
            link=item.get("url","")
            if not link or not link.startswith("https://"):
                continue
            links[link]={"url":link,"publisher":item.get("publisher"),
                         "discovery_channel":item.get("discovery_source") or channel,
                         "date_basis":item.get("date_basis","reported_source_date")}
        all_pub_dates=[x.get("published_at") for x,_ in items if x.get("published_at")]
        out["id"]=hashlib.sha256(key.encode()).hexdigest()[:20]
        out["article_links"]=list(links.values())[:20]
        out["number_of_article_links"]=len(links)
        out["source_channels"]=sorted(set(x.get("discovery_source") or channel for x,channel in items))
        out["published_at"]=min(all_pub_dates) if all_pub_dates else None
        out["content_kind"]="research_report_lead" if any(
            x.get("content_kind")=="research_report_lead" for x,_ in items
        ) else "news_lead"
        out["headline_case_candidate"]=any(x.get("headline_case_candidate",False) for x,_ in items)
        out["banks_mentioned_in_headline"]=sorted(set(
            bank for x,_ in items for bank in x.get("banks_mentioned_in_headline",[])
        ))
        out["amount_strings_in_headline"]=list(dict.fromkeys(
            amount for x,_ in items for amount in x.get("amount_strings_in_headline",[])
        ))[:5]
        # Explicit geographies ONLY; if conflicting same-title sources, don't map.
        locations={(x.get("map_location"),x.get("map_latitude"),x.get("map_longitude"))
            for x,_ in items if x.get("map_location")}
        if len(locations)>1:
            for field in ("map_location","map_latitude","map_longitude","map_province","map_role"):
                out.pop(field,None)
            out["geographic_accuracy"]="ambiguous_headline_geography"
        out["evidence_status"]="unverified_news_lead"
        out["review_status"]="requires_source_review"
        out["index_note"]="Article discovery record, not a confirmed individual incident or bank loss."
        articles.append(out)
    articles.sort(key=lambda x:str(x.get("published_at") or ""),reverse=True)
    DATA.mkdir(exist_ok=True,parents=True)
    output={"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "coverage_note":"Metadata from Google News, RCMP and GDELT. Some reports may be missed; duplicated stories may remain.",
            "raw_discoveries":len(gathered),"unique_headlines":len(articles),
            "articles":articles}
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({"raw_discoveries":len(gathered),"unique_headlines":len(articles),
                      "source_channels":sorted(set(ch for x in articles for ch in x["source_channels"]))}))
if __name__=="__main__":
    build()
