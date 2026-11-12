#!/usr/bin/env python3
"""Build the search index and profile pages data for the Explore UI.

Outputs (deploy-time artifacts under data/explore/, not committed):
  search.json            compact rows for the global search box
  entities.json          institutions with evidence + aliases (map client focus)
  i/<shard>.json         institution profiles, sharded by FNV-1a(id) % 256
  c/<CODE>.json          country profiles
  t/<slug>.json          scam-theme profiles

Profiles only re-arrange records that already exist in the published data.
They add no new claims: every row keeps its source link and evidence label.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "explore"
NEWS_CAP = 150


def load(name, field, default=None):
    path = DATA / name
    if not path.exists():
        return default if default is not None else []
    try:
        payload = json.loads(path.read_text("utf-8"))
    except ValueError:
        return default if default is not None else []
    return payload if field is None else payload.get(field, default if default is not None else [])


def fnv1a(text: str) -> int:
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def shard(ident: str) -> str:
    return format(fnv1a(ident) % 256, "02x")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).casefold()).strip("-")


def write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")


def day(value):
    return str(value or "")[:10] or None


def strip_publisher(title, publisher):
    title = str(title or "")
    publisher = str(publisher or "").strip()
    if publisher and title.endswith(" - " + publisher):
        return title[: -(len(publisher) + 3)]
    return title


def headline_row(item, kind):
    return {
        "kind": kind,
        "id": item.get("id"),
        "date": day(item.get("published_at")),
        "title": strip_publisher(item.get("title"), item.get("publisher")),
        "publisher": item.get("publisher"),
        "url": item.get("url"),
        "evidence": "unverified_headline",
        "sources": item.get("source_count") or item.get("number_of_article_links") or 1,
    }


def official_row(ev, regulator=None):
    return {
        "kind": "enforcement",
        "id": ev.get("id"),
        "date": day(ev.get("published_at")),
        "title": ev.get("title"),
        "publisher": regulator or ev.get("regulator") or ev.get("source"),
        "url": ev.get("source_url"),
        "institution": ev.get("institution"),
        "status": ev.get("status"),
        "penalty": ev.get("penalty_cad") if ev.get("penalty_cad") is not None else ev.get("penalty_amount"),
        "currency": "CAD" if ev.get("penalty_cad") is not None else ev.get("penalty_currency"),
        "evidence": "regulator_published_action",
    }


def lead_row(item):
    return {
        "kind": "regulator_publication",
        "id": item.get("id"),
        "date": day(item.get("first_observed_at")),
        "title": item.get("title"),
        "publisher": item.get("regulator"),
        "url": item.get("source_url"),
        "evidence": item.get("evidence_tier") or "official_publication_lead",
    }


def year_counts(rows):
    counts = defaultdict(Counter)
    for r in rows:
        y = str(r.get("date") or "")[:4]
        if re.fullmatch(r"(19|20)\d\d", y):
            counts[y][r["kind"]] += 1
    return {y: dict(c) for y, c in sorted(counts.items())}


def weight(inst):
    c = inst.get("counts", {})
    od = (inst.get("official_data") or {}).get("counts", {})
    return (5 * c.get("enforcement", 0) + 4 * c.get("incidents", 0) + 3 * c.get("regulator_publications", 0)
            + c.get("headlines", 0) + sum(v for v in od.values() if isinstance(v, (int, float))))


CANADIAN_REGULATORS = {"FINTRAC", "FCAC", "CIRO", "OSC", "BCSC", "AMF", "OSFI", "ASC", "FSRA"}


def jurisdiction(inst):
    """Where the organisation is registered, from official registers only."""
    ident = inst.get("id", "")
    od = inst.get("official_data") or {}
    if ident.startswith("us-") or any(k in od for k in ("fdic", "ncua", "occ")):
        return "US"
    if any(k in od for k in ("osfi", "amf_registrations", "obsi_firm_complaints", "bank_disclosures")):
        return "CA"
    return None


def acted_in(inst):
    """Countries whose regulators published actions naming it."""
    out = list(inst.get("enforcement_countries") or [])
    od = inst.get("official_data") or {}
    canadian = any(od.get(k) for k in ("fintrac_notices", "fcac_notices", "ciro_concluded_cases")) or any(
        e.get("kind") == "enforcement" and str(e.get("source") or "").upper() in CANADIAN_REGULATORS
        for e in inst.get("evidence") or [])
    if canadian and "CA" not in out:
        out.append("CA")
    return out


def build():
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    graph = load("institution_intelligence.json", None, {})
    institutions = graph.get("institutions", [])
    countries = load("world_jurisdictions.json", "jurisdictions")
    global_events = load("global_enforcement.json", "events")
    ca_events = load("events.json", "events")
    leads = load("global_regulator_publications.json", "leads")
    world = load("world_reporting.json", "leads")
    groups = load("reporting_groups.json", "groups")
    incidents = load("incidents.json", "incidents")
    trends = load("theme_trends.json", None, {})
    mentions = load("headline_entities.json", None, {}).get("articles", {})

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    by_id = {x["id"]: x for x in institutions}
    inst_jur = {x["id"]: jurisdiction(x) for x in institutions}
    inst_acted = {x["id"]: acted_in(x) for x in institutions}

    # ---------------- institution profiles (sharded)
    shards = defaultdict(dict)
    for inst in institutions:
        profile = {k: inst.get(k) for k in ("id", "name", "legal_name", "aliases", "counts", "themes",
                                            "annual_penalties_cad", "recent_activity", "official_data")}
        profile["jurisdiction"] = inst_jur[inst["id"]]
        profile["acted_in"] = inst_acted[inst["id"]]
        profile["evidence"] = inst.get("evidence", [])
        profile["years"] = year_counts([{"date": e.get("date"), "kind": e.get("kind")} for e in profile["evidence"]])
        shards[shard(inst["id"])][inst["id"]] = profile
    for key, rows in shards.items():
        write(OUT / "i" / f"{key}.json", rows)

    # ---------------- country profiles
    country_names = {c["code"]: c["name"] for c in countries}
    official_by_cc = defaultdict(list)
    for ev in global_events:
        official_by_cc[ev.get("country_code")].append(official_row(ev))
    for ev in ca_events:
        official_by_cc["CA"].append(official_row(ev, ev.get("source")))
    leads_by_cc = defaultdict(list)
    for item in leads:
        leads_by_cc[item.get("country_code")].append(lead_row(item))
    news_by_cc = defaultdict(list)
    for item in world:
        if item.get("country_code"):
            news_by_cc[item["country_code"]].append(headline_row(item, "headline"))
    for item in groups:  # Canadian reporting groups
        news_by_cc["CA"].append(headline_row(item, "headline"))
    inst_by_cc = defaultdict(list)
    for inst in institutions:
        if not (inst["counts"].get("enforcement") or inst["counts"].get("headlines")
                or inst["counts"].get("incidents") or inst["counts"].get("regulator_publications")):
            continue
        w = weight(inst)
        for cc in {inst_jur[inst["id"]], *inst_acted[inst["id"]]} - {None}:
            inst_by_cc[cc].append((w, {"id": inst["id"], "name": inst["name"], "counts": inst["counts"]}))

    country_rows = []
    for c in countries:
        cc = c["code"]
        official = sorted(official_by_cc.get(cc, []), key=lambda r: r["date"] or "", reverse=True)
        pubs = sorted(leads_by_cc.get(cc, []), key=lambda r: r["date"] or "", reverse=True)
        news = sorted(news_by_cc.get(cc, []), key=lambda r: r["date"] or "", reverse=True)
        insts = [x for _, x in sorted(inst_by_cc.get(cc, []), key=lambda t: -t[0])[:40]]
        timeline = official + pubs + news[:NEWS_CAP]
        profile = {
            "code": cc, "name": c["name"],
            "coverage": {k: c.get(k) for k in ("coverage", "regulator_feed_status", "world_reporting_state",
                                               "agency_count", "enforcement_count", "world_reporting_count",
                                               "official_publication_lead_count")},
            "counts": {"enforcement": len(official), "regulator_publications": len(pubs), "headlines": len(news),
                       "institutions": len(inst_by_cc.get(cc, []))},
            "years": year_counts(official + pubs + news),
            "timeline": sorted(timeline, key=lambda r: r["date"] or "", reverse=True),
            "news_total": len(news),
            "institutions": insts,
        }
        if cc == "CA":
            profile["incidents"] = [{
                "kind": "incident", "id": i.get("id"), "date": day(i.get("reported_at")), "title": i.get("title"),
                "publisher": i.get("source_name"), "url": i.get("source_url"), "evidence": i.get("evidence_status"),
            } for i in incidents]
            profile["counts"]["incidents"] = len(incidents)
            profile["timeline"] = sorted(profile["timeline"] + profile["incidents"],
                                         key=lambda r: r["date"] or "", reverse=True)
        write(OUT / "c" / f"{cc}.json", profile)
        total = len(official) + len(pubs) + len(news)
        if total:
            country_rows.append((cc, c["name"], len(official), len(news), total))

    # ---------------- theme profiles
    theme_rows = []
    group_by_theme = defaultdict(list)
    for item in groups:
        for theme in item.get("fraud_themes") or []:
            group_by_theme[theme].append(item)
    for theme in trends.get("themes", []):
        name = theme["name"]
        items = sorted(group_by_theme.get(name, []), key=lambda x: x.get("published_at") or "", reverse=True)
        inst_counter = Counter()
        for item in items:
            for ident in mentions.get(item.get("id"), []):
                inst_counter[ident] += 1
        profile = {
            "slug": slug(name), "name": name,
            "year_counts": theme.get("year_counts", {}),
            "total_headlines": theme.get("total_headlines", len(items)),
            "publisher_count": theme.get("publisher_count"),
            "timeline": [headline_row(x, "headline") for x in items[:NEWS_CAP]],
            "institutions": [{"id": k, "name": by_id[k]["name"], "mentions": n}
                             for k, n in inst_counter.most_common(20) if k in by_id],
            "note": "Theme counts measure news coverage that matches keywords, not incidence of fraud.",
        }
        write(OUT / "t" / f"{slug(name)}.json", profile)
        theme_rows.append((slug(name), name, profile["total_headlines"]))

    # ---------------- search index (compact rows)
    # [type, id, label, sub, weight, extra-search-text, target]
    # target: event source URL, or the country code a world headline belongs to.
    rows = []
    registry = []  # register-only entries (mostly US FDIC/NCUA), loaded second
    for inst in institutions:
        c = inst["counts"]
        bits = []
        if c.get("enforcement"):
            bits.append(f"{c['enforcement']} regulator action{'s' if c['enforcement'] != 1 else ''}")
        if c.get("regulator_publications"):
            bits.append(f"{c['regulator_publications']} regulator publications")
        if c.get("incidents"):
            bits.append(f"{c['incidents']} reviewed cases")
        if c.get("headlines"):
            bits.append(f"{c['headlines']} news mentions")
        od = inst.get("official_data") or {}
        if od.get("sanctions_designations"):
            bits.append("sanctions list")
        if not bits:
            reg = [k for k in ("osfi", "fdic", "ncua", "occ", "amf_registrations") if od.get(k)]
            bits.append({"osfi": "OSFI register", "fdic": "FDIC register", "ncua": "NCUA register",
                         "occ": "OCC records", "amf_registrations": "AMF register"}.get(reg[0], "Official register")
                        if reg else "Official record")
        jur = inst_jur[inst["id"]]
        where = jur or "/".join(inst_acted[inst["id"]][:3])
        sub = (where + " · " if where else "") + " · ".join(bits[:3])
        aliases = [a for a in (inst.get("aliases") or []) if a != inst["name"]][:4]
        row = ["i", inst["id"], inst["name"], sub, weight(inst), " ".join(aliases), None]
        evidence = any(c.get(k) for k in ("enforcement", "incidents", "headlines", "regulator_publications"))
        (registry if jur == "US" and not evidence and not od.get("sanctions_designations") else rows).append(row)
    for cc, name, n_off, n_news, total in country_rows:
        rows.append(["c", cc, name, f"{n_off} official actions · {n_news} news mentions", 50 + total, cc, None])
    for s, name, total in theme_rows:
        rows.append(["t", s, name, f"Scam pattern · {total} headlines", 80 + total, "", None])
    for ev in global_events + ca_events:
        rows.append(["e", ev.get("id"), ev.get("title") or ev.get("institution"),
                     f"{ev.get('regulator') or ev.get('source')} · {day(ev.get('published_at')) or 'date n/a'}",
                     6, ev.get("institution") or "", ev.get("source_url")])
    for item in groups:
        rows.append(["h", item.get("id"), strip_publisher(item.get("title"), item.get("publisher")),
                     f"{item.get('publisher') or 'News'} · {day(item.get('published_at')) or ''}", 1, "", None])
    for item in world:
        rows.append(["w", item.get("id"), strip_publisher(item.get("title"), item.get("publisher")),
                     f"{item.get('country') or ''} · {item.get('publisher') or 'News'} · {day(item.get('published_at')) or ''}",
                     1, "", item.get("country_code") or None])
    write(OUT / "search.json", {"generated_at": generated, "rows": rows})
    write(OUT / "search_registry.json", {"generated_at": generated, "rows": registry})

    entities = [{"name": x["name"], "aliases": x.get("aliases", [])} for x in institutions
                if any(x["counts"].get(k) for k in ("enforcement", "incidents", "headlines", "regulator_publications"))]
    write(OUT / "entities.json", {"generated_at": generated, "institutions": entities,
                                  "countries": [{"code": c["code"], "name": c["name"]} for c in countries]})

    summary = {"institution_shards": len(shards), "institutions": len(institutions),
               "countries": len(countries), "countries_with_evidence": len(country_rows),
               "themes": len(theme_rows), "search_rows": len(rows), "registry_rows": len(registry), "entities_with_evidence": len(entities)}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    build()
    sys.exit(0)
