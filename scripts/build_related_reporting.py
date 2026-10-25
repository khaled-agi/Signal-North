#!/usr/bin/env python3
"""Suggest defensible, source-linked relationships between reporting groups.

A connection is a *research prompt*, not a verified incident merge or fraud
finding. The existing reporting-group and original article datasets remain
immutable.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from .build_story_groups import meaningful, when
except ImportError:
    from build_story_groups import meaningful, when

DATA=Path(__file__).resolve().parents[1]/"data"
GENERIC={"canada","canadian","scam","fraud","scams","frauds","bank","banks",
         "investor","investors","money","report","reports","reporting",
         "alleged","online","police","investigation","million","thousand"}

def facts(item):
    entity=set(item.get("banks_mentioned_in_headline") or [])|set(item.get("organizations_mentioned_in_headline") or [])
    return {
      "entities":entity,
      "themes":set(item.get("fraud_themes") or []),
      "place":str(item.get("map_location") or "").strip().casefold(),
      "words":meaningful(item.get("title"))-GENERIC,
      "date":when(item)
    }

def assess(a,b):
    left,right=facts(a),facts(b)
    if left["date"] is None or right["date"] is None:return None
    delta=abs((left["date"]-right["date"]).days)
    if delta>180:return None
    entities=left["entities"]&right["entities"]
    themes=left["themes"]&right["themes"]
    words=left["words"]&right["words"]
    geo=bool(left["place"] and right["place"] and left["place"]==right["place"])
    if not (entities or (len(words)>=5 and (themes or geo))):return None
    # Different named entities may be reporting the same multi-institution
    # story; flag for comparison but do not merge or impute responsibility.
    score=4*bool(entities)+min(4,len(words))+2*bool(themes)+2*geo+(2 if delta<=10 else 1 if delta<=45 else 0)
    if score<7:return None
    reasons=[]
    if entities:reasons.append("Same organization explicitly named: "+", ".join(sorted(entities)[:3]))
    if len(words)>=3:reasons.append(str(len(words))+" shared descriptive headline terms")
    if themes:reasons.append("Overlapping scam method: "+", ".join(sorted(themes)[:2]))
    if geo:reasons.append("Same source-mentioned place")
    if delta<=10:reasons.append("Published within ten days")
    elif delta<=45:reasons.append("Published within 45 days")
    return {"score":score,"reasons":reasons}

def generate(groups,max_per_group=4):
    by_id={x["id"]:x for x in groups}
    buckets=defaultdict(list)
    # Narrow comparisons by explicit entities and less-common headline terms.
    token_counts=defaultdict(int)
    for x in groups:
        for term in facts(x)["words"]:token_counts[term]+=1
    for x in groups:
        f=facts(x)
        keys={("entity",name) for name in f["entities"]}
        keys.update(("word",word) for word in f["words"] if token_counts[word]<=100)
        for key in keys:buckets[key].append(x["id"])
    candidates=defaultdict(set)
    for values in buckets.values():
        if len(values)>140:continue
        for i,first in enumerate(values):
            for second in values[i+1:]:
                candidates[first].add(second)
                candidates[second].add(first)
    results={}
    comparisons=0
    for gid,other_ids in candidates.items():
        item=by_id[gid]
        matches=[]
        for other_id in other_ids:
            detail=assess(item,by_id[other_id]);comparisons+=1
            if not detail:continue
            other=by_id[other_id]
            matches.append({
              "group_id":other_id,
              "title":other.get("title"),
              "published_at":other.get("published_at"),
              "source_url":other.get("url"),
              "publisher":other.get("publisher"),
              "shared_indicators":detail["reasons"],
              "research_priority":detail["score"],
              "relationship_status":"unverified_research_lead",
            })
        if matches:
            matches.sort(key=lambda x:(-x["research_priority"],x.get("published_at") or "",x["group_id"]))
            results[gid]=matches[:max_per_group]
    return results,comparisons

def main():
    p=DATA/"reporting_groups.json"
    grouped=json.loads(p.read_text("utf-8"))
    groups=grouped.get("groups",[])
    results,checks=generate(groups)
    output={
      "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "reporting_groups_analyzed":len(groups),
      "groups_with_suggested_connections":len(results),
      "candidate_comparisons":checks,
      "methodology":"Possible links by overlap in named organizations, descriptive headline words, scam themes, source-mentioned city and timing. These are NOT confirmed same incidents, causal relationships, accused parties or corroborated facts. Review original sources.",
      "connections":results
    }
    (DATA/"related_reporting.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({k:v for k,v in output.items() if k!="connections"},indent=2))

if __name__=="__main__":
    main()
