#!/usr/bin/env python3
"""Worldwide, *unverified* fraud-news discovery via country-specific RSS searches.

Not official enforcement or a country crime-incidence dataset. Search markets are
NOT verified incident locations. A rotating budget covers all ISO-3166 markets
over multiple scheduled runs; no fabricated markers for empty/unattempted feeds.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pycountry
import requests
try:
    from .world_country_lenses import country_profile, CRIME_TERMS, research_jurisdictions, country_title_reference, LANGUAGE_PROXY_EDITIONS, NEWS_EDITIONS
except ImportError:
    from world_country_lenses import country_profile, CRIME_TERMS, research_jurisdictions, country_title_reference, LANGUAGE_PROXY_EDITIONS, NEWS_EDITIONS

DATA=Path(__file__).resolve().parents[1]/"data"
FEED=DATA/"world_reporting.json"
STATUS=DATA/"world_reporting_status.json"
STATE=DATA/"world_reporting_state.json"
HEADERS={"User-Agent":"SignalNorthPublicResearch/0.9 (+https://github.com/khaled-agi/Signal-North; metadata-only news discovery)"}
MAX_AGE_DAYS=120
MAX_PER_COUNTRY=90
MAX_ALL=12000
DEFAULT_BATCH=32
ENGLISH_TERMS=('fraud','scam','money laundering','bank phishing')
TITLE_RELEVANCE_TERMS=tuple(x.casefold() for x in CRIME_TERMS)
FINANCE_TERMS=re.compile(
 r"\b(bank|banking|financial|fintech|securities|payments?|insurance|investment|aml|"
 r"anti.money laundering|money changer|crypto|credit union|financ(?:e|ial)|"
 r"banco|banca|banque|banque centrale|regulador financiero|banqueiro|"
 r"البنك|مصرف|مالي|银行|銀行|金融|은행|금융)\b",re.I)
ENFORCEMENT_TERMS=re.compile(
 r"\b(fine[ds]?|fined|penalt(?:y|ies)|sanction|settlement|enforcement action|"
 r"prohibition order|revok(?:ed|ation)|administrative order|regulator fines?|"
 r"amende|multa|sanci[oó]n|bu(?:ß|ss)geld|geldbu(?:ß|ss)e|penalidade|"
 r"处罚|罚款|벌금)\b",re.I)
QUERY_DAYS=30

def now():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")

def read(path,default):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return default

def save(path,payload):
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n","utf-8")

def markets():
    return [country_profile(x) for x in research_jurisdictions()]

def choose_batch(all_markets,cursor,batch_size):
    if not all_markets:return [],0
    size=min(len(all_markets),max(1,int(batch_size)))
    start=int(cursor)%len(all_markets)
    return [all_markets[(start+i)%len(all_markets)] for i in range(size)],(start+size)%len(all_markets)

def search_queries(profile):
    name=profile["name"].replace('"',"")
    # The country name is a search constraint, NOT proof that a reported incident
    # took place in that country.
    queries=[
        f'"{name}" (fraud OR scam OR phishing) when:{QUERY_DAYS}d',
        f'"{name}" ("money laundering" OR "financial crime" OR "investment scam" OR "fraud enforcement") when:{QUERY_DAYS}d',
        f'"{name}" (bank fined OR "financial regulator penalty" OR "anti-money laundering fine") when:{QUERY_DAYS}d',
    ]
    if profile["local_term"] and profile["local_country_term"] and profile["local_language"]!="en":
        queries.append(f'{profile["local_term"]} "{profile["local_country_term"]}" when:{QUERY_DAYS}d')
    return queries

def is_local_query(profile,query):
    """Whether this query uses curated native-language search terms."""
    return bool(profile.get("local_language") not in (None,"en")
        and query==search_queries(profile)[-1])

def query_edition(profile,query):
    """Google News UI/feed edition, not a claim of article or source language.

    English searches deliberately use English editions, while native-language
    searches use a matching national edition where supported, otherwise a
    labeled same-language proxy. Unlisted languages fall back to en-US
    discovery with original native-script keywords.
    """
    code=profile["code"]
    known=NEWS_EDITIONS.get(code)
    if is_local_query(profile,query):
        language=profile["local_language"]
        if known and known[0].split("-")[0]==language:
            return known,"local_country_edition"
        proxy=LANGUAGE_PROXY_EDITIONS.get(language)
        if proxy:return proxy,"language_proxy_edition"
        return ("en-US","US","en"),"native_query_english_edition_fallback"
    if known and known[0].split("-")[0]=="en":
        return known,"english_country_edition"
    return ("en-US","US","en"),"english_global_edition"

def feed_url(profile,query):
    edition,_basis=query_edition(profile,query)
    hl,gl,ceid=edition
    params={"q":query,"hl":hl,"gl":gl,"ceid":gl+":"+ceid}
    return "https://news.google.com/rss/search?"+urlencode(params)

def safe_link(raw):
    if not isinstance(raw,str):return None
    p=urlsplit(raw.strip())
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        return None
    return raw.strip() if len(raw)<2048 else None

def item_date(raw):
    try:
        result=parsedate_to_datetime(raw)
        if not result.tzinfo:result=result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (TypeError,ValueError,IndexError,OverflowError):
        return None

def classify(title,profile):
    t=title.casefold()
    regulatory=bool(FINANCE_TERMS.search(title) and ENFORCEMENT_TERMS.search(title))
    if regulatory:
        return "Reported financial regulatory enforcement (unverified)"
    local_term=(profile.get("local_term") or "").casefold()
    relevant=any(term in t for term in TITLE_RELEVANCE_TERMS) or bool(
        local_term and re.search(r"(?<!\w)"+re.escape(local_term)+r"(?!\w)",t)
    )
    if not relevant:
        return None
    if any(x in t for x in ("launder","blanchiment","blanqueo","lavado de dinero","غسل الأموال")):
        return "Money laundering / AML"
    if any(x in t for x in ("phish","hacked","account takeover","ransomware","اختراق","ไซเบอร์")):
        return "Cyber / account compromise"
    if any(x in t for x in ("investment","crypto","ponzi","investimento","inversión","استثمار")):
        return "Investment / crypto fraud"
    return "Fraud and scam reporting"

def parse_feed(raw,profile,query,observed_at):
    root=ET.fromstring(raw)
    cutoff=observed_at-timedelta(days=MAX_AGE_DAYS)
    results=[]
    for item in root.findall(".//channel/item")[:90]:
        title=" ".join((item.findtext("title") or "").split())[:300]
        link=safe_link(item.findtext("link"))
        pub=item_date(item.findtext("pubDate"))
        category=classify(title,profile)
        if not title or not link or not pub or not category or pub<cutoff or pub>observed_at+timedelta(days=1):
            continue
        country_term=country_title_reference(title,profile)
        if not country_term:
            # RSS market context is not evidence of country relevance.
            # Do not publish unrelated Orlando/Alberta stories under Jordan.
            continue
        src=item.find("source")
        publisher=" ".join((src.text or "").split())[:100] if src is not None else "RSS discovery"
        edition,edition_basis=query_edition(profile,query)
        native_query=is_local_query(profile,query)
        key=(profile["code"]+"|"+title.casefold()+"|"+publisher.casefold())
        results.append({
            "id":"world-news-"+hashlib.sha256(key.encode()).hexdigest()[:20],
            "title":title,"url":link,"publisher":publisher,
            "published_at":iso(pub),"first_seen_at":iso(observed_at),
            "country_code":profile["code"],"country":profile["name"],
            "country_basis":"country_explicitly_named_in_title_not_incident_location",
            "country_reference_status":"country_name_in_headline_not_incident_location",
            "country_reference_term":country_term,
            "source_market":edition[1],
            "query_language":profile["local_language"] if native_query else "en",
            "query_edition":edition[1]+":"+edition[2],
            "query_edition_basis":edition_basis,
            "language_strategy":profile["language_strategy"],
            "search_language":profile["local_language"] if native_query else "en",
            "category":category,"evidence_status":"unverified_news_lead",
            "review_status":"not_source_reviewed",
            "source_kind":"country_localized_news_search",
            "date_basis":"rss_publication_date",
            "geolocation_accuracy":"no_event_coordinates",
        })
    return results

def fetch_query(profile,query,observed_at):
    response=requests.get(feed_url(profile,query),timeout=17,headers=HEADERS)
    response.raise_for_status()
    if len(response.content)>1_500_000:raise ValueError("feed too large")
    return parse_feed(response.content,profile,query,observed_at)

def collect_market(profile,observed_at):
    combined={}
    failures=[]
    attempts=0
    for query in search_queries(profile):
        attempts+=1
        try:
            for item in fetch_query(profile,query,observed_at):
                combined[item["id"]]=item
        except (requests.RequestException,ET.ParseError,ValueError) as exc:
            failures.append(type(exc).__name__)
    return list(combined.values()),{
        "state":"partial_error" if failures and len(failures)<attempts else
                "error" if failures else "reporting_found" if combined else "attempted_empty",
        "attempted_at":iso(observed_at),
        "queries_attempted":attempts,
        "local_queries_attempted":int(bool(profile.get("local_language") not in (None,"en") and profile.get("local_term"))),
        "accepted":len(combined),"errors":failures[:3],
    }

def retained(leads,observed_at):
    cutoff=observed_at-timedelta(days=MAX_AGE_DAYS)
    by_country={}
    for item in leads:
        if item.get("evidence_status")!="unverified_news_lead" or item.get("source_kind")!="country_localized_news_search":
            continue
        published=item.get("published_at") or ""
        if not re.match(r"^\d{4}-\d\d-\d\dT",str(published)):continue
        try:dt=datetime.fromisoformat(published)
        except ValueError:continue
        if not (cutoff<=dt<=observed_at+timedelta(days=1)):continue
        code=str(item.get("country_code") or "")
        if len(code)!=2 or code not in {m.alpha_2 for m in research_jurisdictions()}:continue
        country=next((m for m in research_jurisdictions() if m.alpha_2==code),None)
        if country is None:continue
        profile=country_profile(country)
        term=country_title_reference(item.get("title",""),profile)
        if not term:continue
        item["country_basis"]="country_explicitly_named_in_title_not_incident_location"
        item["country_reference_status"]="country_name_in_headline_not_incident_location"
        item["country_reference_term"]=term
        by_country.setdefault(code,{})[item["id"]]=item
    rows=[]
    for group in by_country.values():
        rows.extend(sorted(group.values(),key=lambda x:x["published_at"],reverse=True)[:MAX_PER_COUNTRY])
    return sorted(rows,key=lambda x:x["published_at"],reverse=True)[:MAX_ALL]

def run():
    DATA.mkdir(parents=True,exist_ok=True)
    ts=now()
    profiles=markets()
    previous=read(FEED,{"leads":[]})
    last=read(STATUS,{"countries":{}})
    progress=read(STATE,{"next_cursor":0})
    batch_size=min(64,max(1,int(os.environ.get("WORLD_NEWS_BATCH",str(DEFAULT_BATCH)))))
    chosen,next_cursor=choose_batch(profiles,progress.get("next_cursor",0),batch_size)
    existing={r["id"]:r for r in retained(previous.get("leads",[]),ts)}
    status={**last.get("countries",{})}
    if os.environ.get("WORLD_NEWS_OFFLINE")=="1":
        # Tests and manual dry runs should not erase historical results or
        # claim discovery was attempted.
        chosen=[]; next_cursor=progress.get("next_cursor",0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs={pool.submit(collect_market,p,ts):p for p in chosen}
        for fut in as_completed(jobs):
            profile=jobs[fut];code=profile["code"]
            try:
                found,report=fut.result()
            except Exception as e:
                found=[];report={"state":"error","attempted_at":iso(ts),"queries_attempted":0,
                                "accepted":0,"errors":[type(e).__name__]}
            if report["state"]!="error":
                for lead in found:
                    if lead["id"] in existing:
                        lead["first_seen_at"]=existing[lead["id"]].get("first_seen_at",lead["first_seen_at"])
                    existing[lead["id"]]=lead
            status[code]={**report,"name":profile["name"],
                "language_strategy":profile["language_strategy"],
                "last_nonempty_at":iso(ts) if found else status.get(code,{}).get("last_nonempty_at")}
    final=retained(existing.values(),ts)
    total_attempted=sum(bool(v.get("attempted_at")) for v in status.values())
    count_codes=len({x["country_code"] for x in final})
    save(FEED,{"updated_at":iso(ts),"leads":final,
        "methodology":"Only headlines explicitly mentioning a country or its curated local name are attributed to that country. Mentions are NOT incident locations. RSS search-market results without country evidence are rejected, including older false-positive records. Non-exhaustive public metadata."})
    save(STATUS,{"last_completed_at":iso(ts),"market_count":len(profiles),
        "markets_attempted":total_attempted,"markets_with_current_news":count_codes,
        "current_leads":len(final),"batch_size":len(chosen),"next_cursor":next_cursor,
        "local_language_markets_configured":sum(
            bool(p["local_term"] and p["local_language"]!="en") for p in profiles),
        "markets_with_local_queries_attempted":sum(
            bool(v.get("local_queries_attempted",0)) for v in status.values()),
        "countries":status,
        "coverage_note":"Rotating RSS sampling with explicit headline-country mention checks. Not all local reporting and not incident geography. No accepted results do not imply no fraud."})
    save(STATE,{"next_cursor":next_cursor})
    print(json.dumps({"markets":len(profiles),"attempted":total_attempted,
                      "in_this_batch":len(chosen),"market_news":count_codes,"recent_leads":len(final)}))

if __name__=="__main__":
    run()
