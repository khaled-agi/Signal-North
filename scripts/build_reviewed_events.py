#!/usr/bin/env python3
"""Compile Signal North's reviewed-event records from explicitly curated evidence.

No automated article, related-report suggestion, or social tip can create a
reviewed event. Legacy source-reviewed cases retain their attribution and
uncertainties. Future manually reviewed events require documented provenance.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parents[1] / "data"
ROLES = {
    "customer_financial_institution",
    "institution_impersonated",
    "bank_not_identified",
    "unnamed_financial_institution_assisted_recovery",
    "affected_payment_provider", "subject_of_investigation",
    "regulator", "named_in_reporting_no_role_established",
}
AMOUNTS = {
    "victim_reported_loss", "unauthorized_credit_exposure", "recovered_amount",
    "bank_borne_loss", "regulatory_penalty", "amount_not_specified",
}
CLAIM_STATUS = {"source_attributed", "officially_reported", "independently_corrobated"}
# Do not accept claims that imply formal legal proof unless human-reviewed.
SOURCE_STATUS = {"reported_by_news", "police_release", "government_release",
                 "regulator_primary", "court_document", "original_publication"}

def load(name,key):
    p = DATA / name
    if not p.exists():
        return []
    obj=json.loads(p.read_text("utf-8"))
    return obj.get(key,[])

def valid_url(value):
    try:
        u=urlparse(str(value))
        return u.scheme=="https" and bool(u.hostname)
    except (TypeError,ValueError):
        return False

def source_type(e):
    return e.get("evidence_status") if e.get("evidence_status") in SOURCE_STATUS else "original_publication"

def from_curated_case(case):
    cid=case["id"]
    url=case.get("source_url")
    if not valid_url(url):
        raise ValueError(f"Reviewed case {cid}: no valid primary/source reporting URL")
    sid=f"source:{cid}:1"
    period=case.get("incident_period") or None
    role=case.get("institution_role") or "bank_not_identified"
    if role not in ROLES:
        raise ValueError(f"{cid}: unknown institution role {role}")
    sources=[{
        "id":sid,"url":url,
        "publisher":case.get("source_name") or "Named original source",
        "publication_date":case.get("reported_at"),
        "document_type":source_type(case),
        "provenance":"legacy_curated_source_attribution",
        "full_text_preserved":False,
    }]
    claims=[{
        "id":f"{cid}:claim:summary","statement":case.get("summary") or case["title"],
        "kind":"reported_narrative","source_ids":[sid],
        "certainty":"source_attributed",
        "qualification":case.get("disclaimer") or "Attributed reporting; not an independent finding.",
    }]
    financial=[]
    amount=case.get("amount_cad")
    if amount is not None:
        kind=case.get("amount_type")
        if kind not in AMOUNTS:
            raise ValueError(f"{cid}: unsupported monetary category {kind}")
        financial=[{
            "value":amount,"currency":"CAD","type":kind,
            "approximate":bool(case.get("amount_approximate",False)),
            "attributed_to":"customer" if kind=="victim_reported_loss" else
                            "recovery" if kind=="recovered_amount" else
                            "credit_exposure" if kind=="unauthorized_credit_exposure" else "unestablished",
            "source_ids":[sid],"certainty":"source_attributed",
            "not_a_bank_loss_unless_explicitly_supported":kind!="bank_borne_loss",
        }]
    stages=case.get("investigation",{}).get("stages") or []
    timeline=[{"step":i+1,"label":entry[0],"narrative":entry[1],
               "event_date":None,"source_ids":[sid],"certainty":"source_attributed"}
              for i,entry in enumerate(stages)]
    institution=case.get("institution")
    entities=[{
        "name":institution,
        "role":role,
        "role_status":"source_attributed",
        "legal_liability_established":False,
        "source_ids":[sid],
    }] if institution else []
    # No private person names or customer identifying information are indexed.
    record={
        "id":cid,
        "title":case["title"],
        "case_type":"reported_financial_fraud",
        "review_state":"source_reviewed",
        "independently_verified":False,
        "review_scope":"published summary reviewed; underlying events not adjudicated",
        "reviewer_id":None,
        "last_reviewed_at":None,
        "publication_date":case.get("reported_at"),
        "incident_period":period,
        "incident_date":case.get("event_date"),
        "fraud_type":case.get("fraud_type"),
        "province":case.get("province"),
        "geography":{
            "label":case.get("location"),
            "role":case.get("location_role"),
            "latitude":case.get("latitude"),
            "longitude":case.get("longitude"),
            "location_is_verified_incident_scene":False,
        },
        "entities":entities,
        "institution_role":role,
        "reported_impact":financial,
        "reported_recovery_outcome":case.get("recovery_status"),
        "sources":sources,
        "claims":claims,
        "timeline":timeline,
        "unanswered_questions":case.get("investigation",{}).get("questions") or [],
        "counterevidence":[],
        "counterevidence_status":"not_assessed",
        "reporting_group_links":[],
        "link_review_status":"not_reviewed",
        "editorial_origin":{"dataset":"data/incidents.json","original_case_id":cid,
                            "record_created_from":"existing_curated_case_summary"},
        "disclaimer":case.get("disclaimer") or "Source-attributed account, not a finding of institutional fault.",
    }
    validate(record,allow_legacy=True)
    return record

def validate(obj,allow_legacy=False):
    required=("id","title","sources","claims","review_state","review_scope",
              "independently_verified","entities","reported_impact","timeline",
              "unanswered_questions","reporting_group_links")
    missing=[k for k in required if k not in obj]
    if missing:raise ValueError(f"{obj.get('id','unknown')}: missing fields {missing}")
    if not obj["sources"]:raise ValueError("At least one original source required")
    if not obj["claims"]:raise ValueError("At least one sourced claim required")
    if obj["independently_verified"] is True and not allow_legacy:
        raise ValueError("Do not assert independent verification without an external adjudication process")
    if not allow_legacy:
        if obj["review_state"]!="editorially_approved":
            raise ValueError("A new event must have explicit editorial approval")
        if not obj.get("reviewer_id") or not obj.get("last_reviewed_at"):
            raise ValueError("A new event needs an identified reviewer and actual review date")
        if not obj.get("review_rationale"):
            raise ValueError("A new event must explain its evidentiary review rationale")
    source_ids={s["id"] for s in obj["sources"]}
    if len(source_ids)!=len(obj["sources"]):raise ValueError("Duplicate source identifiers")
    for src in obj["sources"]:
        if not valid_url(src.get("url")):raise ValueError(f"Source lacks valid HTTPS URL: {src}")
    for row in [*obj["claims"],*obj["timeline"],*obj["reported_impact"],*obj["entities"]]:
        refs=row.get("source_ids") or []
        if not refs or not set(refs).issubset(source_ids):
            raise ValueError(f"Unattributed fact or invalid source reference: {row}")
    for amount in obj["reported_impact"]:
        if amount.get("type") not in AMOUNTS:
            raise ValueError(f"Unknown money type: {amount.get('type')}")
        if amount.get("currency")!="CAD":
            raise ValueError("Non-CAD financial impacts need a verified conversion policy")
    for entity in obj["entities"]:
        if entity.get("role") not in ROLES:raise ValueError("Unknown organization role")
        if entity.get("legal_liability_established") is not False:
            raise ValueError("Do not automatically infer organization liability")
    for link in obj["reporting_group_links"]:
        if not link.get("group_id") or not link.get("review_rationale") or not link.get("source_ids"):
            raise ValueError("Manual group links need rationale and traceable source IDs")
        if not set(link["source_ids"]).issubset(source_ids):
            raise ValueError("Manual group link source is not in approved event sources")
    if not isinstance(obj["unanswered_questions"],list):
        raise ValueError("Questions must be an array")

def review_queue(links,group_list):
    by_id={g["id"]:g for g in group_list}
    items=[];seen=set()
    for gid,matches in links.items():
        if gid not in by_id:continue
        for row in matches:
            other=row["group_id"]
            if other not in by_id:continue
            ids=tuple(sorted((gid,other)))
            if ids in seen:continue
            seen.add(ids)
            a,b=by_id[ids[0]],by_id[ids[1]]
            items.append({
                "id":"candidate:"+ids[0]+":"+ids[1],
                "group_ids":list(ids),
                "headlines":[{"group_id":g["id"],"title":g.get("title"),
                             "source_url":g.get("url"),"publication_date":g.get("published_at"),
                             "source_count":g.get("source_count",1)} for g in (a,b)],
                "reasons":row.get("shared_indicators") or [],
                "priority":row.get("research_priority",0),
                "status":"unverified_suggested_connection",
                "review_steps":["Read both original articles, not only titles",
                  "Determine whether accounts share a victim, transaction, or official case identifier",
                  "Check publication vs incident dates, geography and quoted amounts",
                  "Document conflicting evidence and individual institution roles",
                  "Only an editor can add a sourced relationship to a reviewed event"],
            })
    items.sort(key=lambda x:-x["priority"])
    return items[:250]

def build():
    seed=load("incidents.json","incidents")
    curated=load("reviewed_events_editorial.json","events")
    groups=load("reporting_groups.json","groups")
    candidates=load("related_reporting.json","connections")
    records=[from_curated_case(x) for x in seed]
    ids={x["id"] for x in records}
    all_groups={g["id"] for g in groups}
    for rec in curated:
        validate(rec)
        if rec["id"] in ids:raise ValueError("Editorial event duplicates curated incident id")
        for link in rec["reporting_group_links"]:
            if link["group_id"] not in all_groups:
                raise ValueError("Editorial link refers to unknown reporting group")
        ids.add(rec["id"]);records.append(rec)
    records.sort(key=lambda x:x.get("publication_date") or "",reverse=True)
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    queue=review_queue(candidates,groups)
    output={
        "schema_version":1,"generated_at":now,
        "reviewed_events":len(records),
        "source_reviewed_legacy_records":len(seed),
        "editorially_approved_new_records":len(curated),
        "methodology":"Only previously curated source-attributed cases and manually approved editorial events appear here. No news headline, user tip, or algorithmic relationship is promoted automatically. Source-reviewed does not mean independently verified or adjudicated.",
        "events":records,
    }
    (DATA/"reviewed_events.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n","utf-8")
    (DATA/"event_review_candidates.json").write_text(json.dumps({
        "generated_at":now,"candidate_pairs":len(queue),
        "methodology":"Suggested possible article relationships. These are not verified same incidents and require original-source editorial review.",
        "items":queue,
    },ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({"reviewed_events":len(records),"legacy_source_attributed":len(seed),
                      "new_editorially_approved":len(curated),"suggested_pairs":len(queue)}))

if __name__=="__main__":
    build()
