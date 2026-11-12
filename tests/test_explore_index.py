"""Search index and profile data built for the Explore UI."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import scripts.build_explore_index as ex

ROOT = Path(__file__).resolve().parents[1]


class ShardParityTest(unittest.TestCase):
    def test_python_shard_matches_browser(self):
        ids = ["rbc", "us-fdic-628", "caisse-populaire-acadienne-ltée", "Québec ÉÜ 北京"]
        js = re.search(r"function fnv\(text\) \{.*?\n  \}", (ROOT / "explore.js").read_text("utf-8"), re.S).group(0)
        script = js + "\nconsole.log(JSON.stringify(" + json.dumps(ids) + ".map(fnv)))"
        try:
            out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.skipTest("node unavailable")
        self.assertEqual(json.loads(out), [ex.shard(i) for i in ids])


class BuildTest(unittest.TestCase):
    def test_profiles_and_search(self):
        original_data, original_out = ex.DATA, ex.OUT
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            try:
                ex.DATA, ex.OUT = data, data / "explore"
                fixtures = {
                    "institution_intelligence.json": {"institutions": [
                        {"id": "binance", "name": "Binance", "aliases": ["Binance"], "enforcement_countries": ["US"],
                         "counts": {"enforcement": 1, "incidents": 0, "headlines": 2, "regulator_publications": 0},
                         "official_data": {"fintrac_notices": [{"date": "2024-05-09"}]},
                         "evidence": [{"kind": "enforcement", "date": "2023-11-21", "source": "FinCEN", "location": "United States"},
                                      {"kind": "headline", "date": "2026-01-02", "id": "g1"}], "themes": []},
                        {"id": "us-fdic-1", "name": "Quiet Bank (US · KS)", "aliases": [],
                         "counts": {"enforcement": 0, "incidents": 0, "headlines": 0, "regulator_publications": 0},
                         "official_data": {"fdic": {"cert": "1"}}, "evidence": [], "themes": []},
                    ]},
                    "world_jurisdictions.json": {"jurisdictions": [{"code": "US", "name": "United States"},
                                                                   {"code": "CA", "name": "Canada"}]},
                    "global_enforcement.json": {"events": [{"id": "x", "country_code": "US", "regulator": "FinCEN",
                                                            "title": "Binance matter", "published_at": "2023-11-21",
                                                            "institution": "Binance"}]},
                    "reporting_groups.json": {"groups": [{"id": "g1", "title": "Binance scam - Example", "publisher": "Example",
                                                          "published_at": "2026-01-02", "url": "https://e.x/1",
                                                          "fraud_themes": ["Investment & crypto scams"]}]},
                    "theme_trends.json": {"themes": [{"name": "Investment & crypto scams", "year_counts": {"2026": 1}, "total_headlines": 1}]},
                    "headline_entities.json": {"articles": {"g1": ["binance"]}},
                }
                for name, obj in fixtures.items():
                    (data / name).write_text(json.dumps(obj), "utf-8")
                ex.build()
                out = data / "explore"
                profile = json.loads((out / "i" / (ex.shard("binance") + ".json")).read_text("utf-8"))["binance"]
                self.assertIsNone(profile["jurisdiction"])          # FinCEN action is not a home country
                self.assertEqual(sorted(profile["acted_in"]), ["CA", "US"])
                us = json.loads((out / "c" / "US.json").read_text("utf-8"))
                self.assertEqual(us["counts"]["enforcement"], 1)
                self.assertIn("binance", [x["id"] for x in us["institutions"]])
                ca = json.loads((out / "c" / "CA.json").read_text("utf-8"))
                self.assertEqual(ca["counts"]["headlines"], 1)
                theme = json.loads((out / "t" / "investment-crypto-scams.json").read_text("utf-8"))
                self.assertEqual(theme["institutions"][0]["id"], "binance")
                rows = json.loads((out / "search.json").read_text("utf-8"))["rows"]
                registry = json.loads((out / "search_registry.json").read_text("utf-8"))["rows"]
                self.assertIn("binance", [r[1] for r in rows])
                self.assertEqual([r[1] for r in registry], ["us-fdic-1"])  # register-only rows load second
                self.assertTrue(all(r[6] is None or not str(r[6]).startswith("https://news.google") for r in rows))
            finally:
                ex.DATA, ex.OUT = original_data, original_out


if __name__ == "__main__":
    unittest.main()
