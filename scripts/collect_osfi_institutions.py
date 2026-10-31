#!/usr/bin/env python3
"""Fetch Canada's official OSFI regulated-financial-institution CSV.

The output is a source-labeled registry, not evidence of wrongdoing.
Fails safely: never replaces an existing good file on source failure.
"""
import csv
import io
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://open.canada.ca/data/dataset/b27ec3ef-7338-4e76-a6fd-128339a92df5/resource/945045fa-2de0-47d4-aad2-144d69467824/download/who_we_regulate_fi_eng.csv"
OUTPUT = Path("data/osfi_institutions.json")
MAX_BYTES = 12_000_000


def fetch():
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "SignalNorthPublicResearch/1.0", "Accept": "text/csv,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        if resp.status != 200:
            raise RuntimeError(f"unexpected HTTP {resp.status}")
        body = resp.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("OSFI response exceeds size limit")
        return body.decode("utf-8-sig")


def normalize(source):
    rows = list(csv.DictReader(io.StringIO(source)))
    if not rows or not rows[0]:
        raise ValueError("OSFI source is empty")
    columns = [c.strip() for c in rows[0].keys() if c]
    if len(columns) < 2:
        raise ValueError("OSFI file has unexpectedly few columns")
    results = []
    for i, raw in enumerate(rows, 1):
        fields = {str(k).strip(): str(v or "").strip() for k, v in raw.items() if k and v is not None}
        if not any(fields.values()):
            continue
        results.append({"source_row": i, "fields": fields})
    if len(results) < 20:
        raise ValueError("OSFI source unusually small; refusing to overwrite")
    return {"source": "OSFI Who We Regulate", "source_url": SOURCE_URL,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source_columns": columns, "record_count": len(results),
            "records": results,
            "scope_note": "Official federally regulated institution listing, not enforcement or wrongdoing."}


def main():
    result = normalize(fetch())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=OUTPUT.parent, encoding="utf-8", delete=False, suffix=".tmp") as tmp:
        json.dump(result, tmp, ensure_ascii=False, separators=(",", ":"))
        name = tmp.name
    os.replace(name, OUTPUT)
    print(f"Validated {result['record_count']} OSFI institutional rows")


if __name__ == "__main__":
    main()
