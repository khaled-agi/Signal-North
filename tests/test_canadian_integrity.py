import json
import unittest
from pathlib import Path
from scripts.collect_fintrac_penalties import parse_html

ROOT = Path(__file__).resolve().parents[1]

class CanadianSourceIntegrity(unittest.TestCase):
    def test_structured_fintrac_parser(self):
        markup = """<table><tbody>
        <tr><td>2026-09-24</td><td>Caisse populaire acadienne ltée, also operating as UNI Financial Cooperation, a federally regulated credit union, was imposed an administrative monetary penalty of $676,500 on July 23, 2026, for committing 3 violations. The case is closed.</td></tr>
        <tr><td>2025-10-22</td><td>Xeltox Enterprises Ltd., also operating as Cryptomus, a money services business, was imposed an administrative monetary penalty of $176,960,190 for committing 2,593 contraventions. Xeltox has appealed the penalty to the Federal Court.</td></tr>
        </tbody></table>"""
        rows = parse_html(markup, minimum=2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["entity_name"], "Caisse populaire acadienne ltée")
        self.assertEqual(rows[0]["penalty_cad"], 676500)
        self.assertEqual(rows[0]["violation_count"], 3)
        self.assertEqual(rows[1]["violation_count"], 2593)
        self.assertEqual(rows[1]["status_summary"], "appealed_or_appeal_reported")

    def test_reject_incomplete_source(self):
        with self.assertRaises(ValueError):
            parse_html("<html><body>Blocked / no data</body></html>", minimum=1)

    def test_known_enforcement_data(self):
        data = json.loads((ROOT / "data/canadian_enforcement_verified.json").read_text(encoding="utf-8"))
        records = data["records"]
        self.assertGreaterEqual(len(records), 30)
        self.assertEqual(len(records), len({
            (r["agency"], r["name"], r["published"], r["penalty_cad"]) for r in records
        }))
        for r in records:
            self.assertTrue(r["url"].startswith("https://"))
            self.assertGreater(r["penalty_cad"], 0)
            self.assertRegex(r["published"], r"^20\d\d-\d\d-\d\d$")

    def test_osfi_snapshot_if_collected(self):
        file = ROOT / "data/osfi_institutions.json"
        if file.exists():
            d = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(d["record_count"], len(d["records"]))
            self.assertGreaterEqual(len(d["records"]), 20)
            self.assertIn("Company Name", d["source_columns"])

    def test_regulator_snapshot_if_collected(self):
        file = ROOT / "data/canadian_regulatory_leads.json"
        if file.exists():
            d = json.loads(file.read_text(encoding="utf-8"))
            self.assertIsInstance(d["leads"], list)
            self.assertIn("sources", d)
            for row in d["leads"]:
                self.assertEqual(row["classification"], "official_index_link_unreviewed")
                self.assertTrue(row["url"].startswith("https://"))

if __name__ == "__main__":
    unittest.main()
