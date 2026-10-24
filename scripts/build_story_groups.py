#!/usr/bin/env python3
"""Deduplicate near-identical reporting into display groups, never inferred incidents.

The raw article index remains unchanged. This second, conservative grouping layer
is a user interface aid for syndicated / lightly reworded coverage. It is NOT an
automated determination that two materially different reports are the same case.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
COMMON = set("""
a an and are as at be been but by canada canadian can for from has have had
in into is it its of on or over that the their them there they this to was were
with about after against amidst amid says said says say news report reports
fraud scam scams frauds police warning warns investigation investigations
""".split())
WORD = re.compile(r"[a-z0-9]+")
AMOUNT = re.compile(r"(?<!\w)\$?\d+(?:[.,]\d+)*(?:k|m|million|billion)?(?!\w)", re.I)
DATE_LIMIT = 10

def normalized(title):
    s = unicodedata.normalize("NFKD", str(title or "").casefold())
    return " ".join(WORD.findall("".join(c for c in s if not unicodedata.combining(c))))

def meaningful(title):
    return {w for w in WORD.findall(normalized(title)) if len(w) >= 3 and w not in COMMON}

def tokens_numbers(title):
    # Contrast quoted dollars/percentages, ages and victim counts. Stripping
    # different numbers would mask a material reporting distinction.
    return set(re.findall(r"(?:\$|c\$)\s?\d[\d,.]*(?:\s?(?:k|m|million|billion))?|\d+(?:\.\d+)?%",str(title or "").casefold()))

def when(item):
    try:
        return datetime.fromisoformat(str(item.get("published_at") or "")[:10]).date()
    except ValueError:
        return None

def is_close(a, b):
    ad, bd = when(a), when(b)
    return ad is not None and bd is not None and abs((ad-bd).days) <= DATE_LIMIT

def compatible_place(a, b):
    a_lat, b_lat = a.get("map_latitude"), b.get("map_latitude")
    a_lon, b_lon = a.get("map_longitude"), b.get("map_longitude")
    if all(isinstance(x,(int,float)) for x in (a_lat,b_lat,a_lon,b_lon)):
        return abs(a_lat-b_lat) < .08 and abs(a_lon-b_lon) < .08
    return True

def likely_same_report(a, b):
    # Avoid false deduplication across dates, cities, named financial entities,
    # monetary figures and unrelated article topics.
    if not is_close(a, b) or not compatible_place(a, b):
        return False
    na,nb = normalized(a.get("title")),normalized(b.get("title"))
    if na == nb and len(na) >= 18:
        return True
    if len(na) < 44 or len(nb) < 44:
        return False
    nums_a, nums_b = tokens_numbers(a.get("title")), tokens_numbers(b.get("title"))
    if nums_a and nums_b and nums_a != nums_b:
        return False
    aa,bb=meaningful(a.get("title")),meaningful(b.get("title"))
    if min(len(aa),len(bb)) < 5:
        return False
    common=len(aa & bb)
    if common < 5:
        return False
    containment=common/min(len(aa),len(bb))
    overlap=2*common/(len(aa)+len(bb))
    # Fully matching rare terms after minor edits, or very high similarity.
    if not (overlap >= .81 and containment >= .89):
        return False
    names_a=set(a.get("banks_mentioned_in_headline") or []) | set(a.get("organizations_mentioned_in_headline") or [])
    names_b=set(b.get("banks_mentioned_in_headline") or []) | set(b.get("organizations_mentioned_in_headline") or [])
    if names_a and names_b and names_a.isdisjoint(names_b):
        return False
    return True

def gather_variants(group):
    variants={}
    for x in group:
        base=[{"title":x.get("title"),"publisher":x.get("publisher"),
               "url":x.get("url"),"published_at":x.get("published_at"),
               "discovery_channel":x.get("discovery_source") or ""}]
        base.extend(x.get("article_links") or [])
        for row in base:
            url=row.get("url")
            if not url or not str(url).startswith("https://"):
                continue
            title=str(row.get("title") or x.get("title") or "").strip()
            key=(str(url),normalized(title))
            variants[key]={"title":title,"publisher":row.get("publisher") or x.get("publisher") or "Original publication",
                "url":str(url),"published_at":row.get("published_at") or x.get("published_at"),
                "discovery_channel":row.get("discovery_channel") or x.get("discovery_source") or ""}
    return sorted(variants.values(),key=lambda x:(x.get("published_at") or "",x["publisher"]),reverse=True)

def display_groups(articles):
    # An inverted index keeps this efficient for thousands of archived titles.
    words_to_seen=defaultdict(set)
    bins=[]
    articles=sorted(articles,key=lambda x:str(x.get("published_at") or ""),reverse=True)
    for row in articles:
        words=meaningful(row.get("title"))
        candidates=set()
        for w in words:
            candidates.update(words_to_seen[w])
        match=None
        for ix in sorted(candidates):
            g=bins[ix]
            if len(g)>=12:
                continue
            # Compare to EACH prior group member, not only the canonical title.
            # This is intentionally strict and uses one best candidate.
            if all(likely_same_report(row,member) for member in g):
                match=ix
                break
        if match is None:
            match=len(bins); bins.append([])
        bins[match].append(row)
        for w in words:
            words_to_seen[w].add(match)
    result=[]
    for group in bins:
        best=sorted(group,key=lambda x:(-len(x.get("article_links") or []),str(x.get("published_at") or "")))[0]
        story=dict(best)
        variants=gather_variants(group)
        ids=[x.get("id") for x in group if x.get("id")]
        story["id"]="report-"+hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:20]
        story["article_ids"]=ids
        story["headline_variations"]=variants
        story["variation_count"]=len(set(normalized(x["title"]) for x in variants))
        story["source_count"]=len(set(x["url"] for x in variants))
        story["underlying_headline_count"]=len(group)
        story["article_links"]=variants
        story["number_of_article_links"]=story["source_count"]
        story["source_channels"]=sorted(set(channel for x in group for channel in (x.get("source_channels") or [])))
        story["banks_mentioned_in_headline"]=sorted(set(z for x in group for z in (x.get("banks_mentioned_in_headline") or [])))
        story["organizations_mentioned_in_headline"]=sorted(set(z for x in group for z in (x.get("organizations_mentioned_in_headline") or [])))
        story["headline_case_candidate"]=any(x.get("headline_case_candidate",False) for x in group)
        # If sources explicitly assign conflicting cities, don't place the
        # grouped record at a misleading single location.
        geos={(x["map_latitude"],x["map_longitude"]) for x in group if isinstance(x.get("map_latitude"),(float,int)) and isinstance(x.get("map_longitude"),(float,int))}
        if len(geos)>1:
            for k in ("map_latitude","map_longitude","map_location","map_province","map_role"):
                story.pop(k,None)
            story["geographic_accuracy"]="multiple_headline_cities_not_geocoded"
        elif len(geos)==1:
            match=next(x for x in group if isinstance(x.get("map_latitude"),(float,int)) and isinstance(x.get("map_longitude"),(float,int)))
            for k in ("map_latitude","map_longitude","map_location","map_province","map_role"):
                if k in match:story[k]=match[k]
        story["evidence_status"]="unverified_grouped_reporting"
        story["review_status"]="requires_source_review"
        story["grouping_basis"]="conservative_headline_similarity_within_10_days"
        story["grouping_disclaimer"]="Grouped reporting about a likely shared publication/topic; does not prove the same underlying victim, incident, loss or misconduct."
        result.append(story)
    result.sort(key=lambda x:str(x.get("published_at") or ""),reverse=True)
    return result

def build():
    raw=json.loads((DATA/"article_index.json").read_text("utf-8"))
    articles=raw.get("articles",[])
    groups=display_groups(articles)
    n=sum(x["underlying_headline_count"] for x in groups)
    assert n==len(articles), f"Missing raw headlines: {len(articles)} vs {n}"
    out={
      "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "original_index_headlines":len(articles),
      "reporting_groups":len(groups),
      "multi_report_groups":sum(x["underlying_headline_count"]>1 for x in groups),
      "methodology":"Display-only high-similarity headline grouping within ten days; original article index preserved. Publisher-specific title wording and original links are retained in each detail view. Groups are not independently verified fraud incidents.",
      "groups":groups
    }
    (DATA/"reporting_groups.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({k:v for k,v in out.items() if k not in ("groups",)}))

if __name__=="__main__":
    build()
