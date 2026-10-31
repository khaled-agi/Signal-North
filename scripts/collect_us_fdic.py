#!/usr/bin/env python3
"""FDIC official institution directory + bank-failure/assistance signals.

- Uses the public BankFind API, not scraped news headlines.
- Separates a regulated bank listing from a bank failure or assistance event.
- Identifies institutions with FDIC CERT, never name-only cross-border matching.
- Maintains last-good snapshots on failures; publishes per-feed health.
- Runs at most daily although the main website workflow runs more frequently.
"""
from __future__ import annotations
import json
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import requests

API_BASES = (
    "https://api.fdic.gov/banks",
    "https://banks.data.fdic.gov/api",
)
ROOT = Path("data")
OUT = {
    "institutions": ROOT / "us_fdic_institutions.json",
    "failures": ROOT / "us_fdic_failures.json",
}
HEALTH = ROOT / "us_fdic_source_health.json"
MAX_PAGE = 1000
MAX_PAGES = 25
REQUEST_TIMEOUT = 45
MAX_BYTES = 7_000_000
FIELDS = {
    "institutions": "NAME,CERT,CITY,STNAME,STALP,FED_RSSD,WEBADDR,ACTIVE,DATEUPDT",
    "failures": "ID,FIN,NAME,CERT,FAILDATE,FAILYR,CITY,PSTALP,RESTYPE,BIDNAME,QBFASSET,QBFDEP",
}
MIN_ROWS = {"institutions": 2500, "failures": 3500}
SOURCE = "FDIC BankFind Suite public API"


def request_json(session, endpoint, params):
    errors = []
    for base in API_BASES:
        try:
            r = session.get(
                f"{base}/{endpoint}",
                params=params,
                headers={"Accept": "application/json",
                         "User-Agent": "SignalNorthPublicResearch/1.0 (official public FDIC data)"},
                timeout=REQUEST_TIMEOUT,
            )
            r.raise_for_status()
            if len(r.content) > MAX_BYTES:
                raise ValueError("Individual FDIC API page too large")
            result = r.json()
            if not isinstance(result, dict) or not isinstance(result.get("data"), list):
                raise ValueError("FDIC API returned unexpected schema")
            return result
        except (requests.RequestException, ValueError) as e:
            errors.append(type(e).__name__)
    raise RuntimeError("All official FDIC API hosts failed: " + ", ".join(errors))


def normalize(row, dataset):
    fields = row.get("data", row)
    if not isinstance(fields, dict):
        return None
    cert = str(fields.get("CERT") or "").strip()
    if cert.endswith(".0"):
        cert = cert[:-2]
    name = str(fields.get("NAME") or "").strip()
    if dataset == "institutions" and (not cert.isdigit() or not name or len(name) > 250):
        return None
    if dataset == "failures" and (not name or len(name) > 250):
        return None
    cert = cert if cert.isdigit() else None
    common = {
        "fdic_cert": cert,
        "institution": name,
        "city": str(fields.get("CITY") or "").strip()[:120],
        "state": str(fields.get("STALP") or fields.get("PSTALP") or fields.get("STNAME") or "").strip()[:80],
        "country": "US",
        "source_kind": "federal_bank_register" if dataset == "institutions" else "fdic_failure_or_assistance",
    }
    if dataset == "institutions":
        return {
            **common,
            "active": str(fields.get("ACTIVE", "1")).upper() in ("1", "TRUE", "Y"),
            "fed_rssd": str(fields.get("FED_RSSD") or "").strip() or None,
            "website": str(fields.get("WEBADDR") or "").strip()[:300] or None,
            "last_updated": str(fields.get("DATEUPDT") or "")[:40] or None,
        }
    raw_id = str(fields.get("ID") or fields.get("FIN") or "").strip()
    stable_uid = raw_id or hashlib.sha256(json.dumps(fields,sort_keys=True,default=str).encode()).hexdigest()[:22]
    return {
        **common,
        "fdic_event_id":stable_uid,
        "failure_date": str(fields.get("FAILDATE") or "")[:40] or None,
        "failure_year": str(fields.get("FAILYR") or "")[:10] or None,
        "resolution_type": str(fields.get("RESTYPE") or "")[:120] or None,
        "acquirer": str(fields.get("BIDNAME") or "")[:200] or None,
        "assets_thousands_usd": fields.get("QBFASSET"),
        "deposits_thousands_usd": fields.get("QBFDEP"),
        "classification_note": "FDIC failure/assistance is a bank resolution event, NOT a financial-crime finding",
    }


def collect(session, dataset):
    """Fetch all pages and refuse truncated, invalid, or duplicate outputs."""
    results = []
    ids = set()
    meta_total = None
    for offset in range(0, MAX_PAGE * MAX_PAGES, MAX_PAGE):
        params = {
            "fields": FIELDS[dataset],
            "limit": MAX_PAGE,
            "offset": offset,
            "sort_by": "CERT" if dataset == "institutions" else "FAILDATE",
            "sort_order": "ASC",
        }
        if dataset == "institutions":
            params["filters"] = "ACTIVE:1"
        page = request_json(session, dataset, params)
        meta = page.get("meta", {})
        if meta_total is None and isinstance(meta, dict):
            total = meta.get("total")
            if total is not None:
                meta_total = int(total)
        values = page["data"]
        for raw in values:
            record = normalize(raw, dataset)
            if record is None:
                continue
            ident = record["fdic_cert"] if dataset == "institutions" else record["fdic_event_id"]
            if ident in ids:
                continue
            ids.add(ident)
            results.append(record)
        if not values or len(values) < MAX_PAGE or (meta_total and offset + len(values) >= meta_total):
            break
    else:
        raise ValueError(f"{dataset}: reached maximum pagination without last page")
    if len(results) < MIN_ROWS[dataset]:
        raise ValueError(f"{dataset}: only {len(results)} valid records, below validated safety floor")
    if meta_total is not None and len(results) < meta_total * 0.98:
        raise ValueError(f"{dataset}: incomplete result ({len(results)} vs reported {meta_total})")
    return results


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as temp:
        json.dump(payload, temp, ensure_ascii=False, separators=(",", ":"))
        staged = temp.name
    os.replace(staged, path)


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    old_health = {}
    if HEALTH.exists():
        try:
            old_health = json.loads(HEALTH.read_text("utf-8"))
        except (OSError, ValueError):
            pass
    health = dict(old_health.get("sources", {}))
    with requests.Session() as session:
        for dataset, output in OUT.items():
            previous = health.get(dataset, {})
            if (output.exists() and previous.get("status") == "success"
                    and previous.get("last_success", "")[:10] == now[:10]
                    and os.getenv("SIGNALNORTH_FORCE_FDIC") != "1"):
                print(f"FDIC {dataset}: valid snapshot already collected today")
                continue
            try:
                records = collect(session, dataset)
                payload = {
                    "source": SOURCE,
                    "endpoint": dataset,
                    "api_docs": "https://api.fdic.gov/banks/docs/",
                    "retrieved_at": now,
                    "record_count": len(records),
                    "jurisdiction": "United States",
                    "unit": "regulated_entity" if dataset == "institutions" else "failure_or_assistance_event",
                    "methodology": "FDIC CERT is the legal-entity join key. A bank failure is not an allegation of money laundering, fraud, or other misconduct.",
                    "records": records,
                }
                atomic_json(output, payload)
                health[dataset] = {
                    "status": "success",
                    "last_success": now,
                    "record_count": len(records),
                    "url": f"https://api.fdic.gov/banks/{dataset}",
                }
                print(f"FDIC {dataset}: {len(records)} official observations", flush=True)
            except Exception as exc:
                health[dataset] = {
                    **previous,
                    "status": "failed_last_good_preserved" if output.exists() else "unavailable",
                    "last_attempt": now,
                    "error_type": type(exc).__name__,
                    "detail": str(exc)[:200],
                    "url": f"https://api.fdic.gov/banks/{dataset}",
                }
                print(f"FDIC {dataset} FAILED: {type(exc).__name__}: {exc}", flush=True)
    atomic_json(HEALTH, {"generated_at": now, "sources": health})


if __name__ == "__main__":
    main()
