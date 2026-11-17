"""Cross-source organisation linking: recall for real names, no false joins."""
import json
import tempfile
import unittest
from pathlib import Path

import scripts.build_intelligence_graph as g
from scripts.entity_resolution import EntityMatcher, core_name, looks_like_organisation


class NameNormalisationTests(unittest.TestCase):
    def test_legal_suffixes_and_accents_fold(self):
        self.assertEqual(core_name("VIP Realty Inc"), core_name("VIP Realty Inc."))
        self.assertEqual(core_name("Caisse populaire acadienne ltée"), "caisse populaire acadienne")
        self.assertEqual(core_name("Bank of America, N.A."), "bank of america")
        self.assertEqual(core_name("Bank of Nova Scotia (The)"), "bank of nova scotia")

    def test_same_entity_from_two_feeds_shares_a_key(self):
        self.assertEqual(g.bank_key("Atlantic Lottery Corporation Inc."), g.bank_key("Atlantic Lottery Corporation"))
        self.assertEqual(g.bank_key("Juba Express Inc"), g.bank_key("JUBA EXPRESS INC."))

    def test_distinct_legal_entities_stay_distinct(self):
        self.assertNotEqual(g.bank_key("RBC Dominion Securities Inc."), g.bank_key("Royal Bank of Canada"))
        self.assertNotEqual(g.bank_key("Wealthsimple Investments Inc."), g.bank_key("Wealthsimple Digital Assets Inc."))

    def test_individuals_are_not_organisations(self):
        self.assertFalse(looks_like_organisation("Robin Crispin William Odey"))
        self.assertFalse(looks_like_organisation("Four individuals in MAS Securities and Futures Act orders"))
        self.assertTrue(looks_like_organisation("Sir Money Changer Pte. Ltd."))


class MatcherTests(unittest.TestCase):
    def setUp(self):
        m = EntityMatcher()
        m.add("juba", "Juba Express Inc.")
        m.add("fdic-1", "West Shore Bank", allow_variant=False)
        m.add("fdic-2", "Open Bank", allow_variant=False)
        m.add("scotia-sec", "Scotia Securities Inc.")
        m.add("wf-occ", "Wells Fargo Bank, N.A.")
        m.add("dup-a", "Northbridge Capital Ltd")
        m.add("dup-b", "Northbridge Capital Inc")
        m.add("rbc", "RBC", curated=True)
        m.add("bofa", "Bank of America", curated=True)
        m.add("us-fdic-9", "TD Bank, N.A.", allow_variant=False)
        m.add("td", "TD Bank", curated=True)
        m.compile()
        self.m = m

    def keys(self, title):
        return [h["key"] for h in self.m.find(title)]

    def test_exact_official_name_links(self):
        self.assertEqual(self.keys("Juba Express fined by FINTRAC"), ["juba"])

    def test_curated_alias_wins_over_register_duplicate(self):
        self.assertEqual(self.keys("Former TD Bank employee pleads guilty"), ["td"])
        self.assertEqual(self.keys("Bank of America penalty draws probe"), ["bofa"])

    def test_place_names_and_lowercase_phrases_do_not_link(self):
        self.assertEqual(self.keys("West Shore RCMP say man used fraudulent ID"), [])
        self.assertEqual(self.keys("Accused used AI to open bank accounts"), [])

    def test_longer_organisation_names_are_not_split(self):
        self.assertEqual(self.keys("Fraudster impersonating Nova Scotia Securities Commission"), [])

    def test_shortened_brand_is_used_only_when_unambiguous(self):
        self.assertEqual(self.keys("Wells Fargo settles AML case"), ["wf-occ"])
        self.assertEqual(self.keys("Northbridge Capital charged"), [])

    def test_single_words_need_curation(self):
        self.assertEqual(self.keys("RBC customer loses savings"), ["rbc"])
        self.assertEqual(self.keys("rbc customer loses savings"), [])


class GraphLinkingTest(unittest.TestCase):
    def test_news_regulator_and_sanctions_join_one_node(self):
        original = g.DATA
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            try:
                g.DATA = path
                fixtures = {
                    "events.json": {"events": [{"id": "e1", "institution": "Juba Express Inc.", "source": "FINTRAC",
                                                "published_at": "2026-01-02", "title": "Penalty", "penalty_cad": 1000}]},
                    "incidents.json": {"incidents": []},
                    "reporting_groups.json": {"groups": [
                        {"id": "g1", "title": "Ottawa remittance firm Juba Express hit with AML penalty", "published_at": "2026-01-05",
                         "url": "https://example.ca/a", "publisher": "Example", "banks_mentioned_in_headline": []},
                        {"id": "g2", "title": "Police warn West Shore residents about scams", "published_at": "2026-01-06",
                         "url": "https://example.ca/b", "publisher": "Example", "banks_mentioned_in_headline": []},
                    ]},
                    "world_reporting.json": {"leads": [
                        {"id": "w1", "title": "UK sanctions Garantex Europe for laundering - Example", "publisher": "Example",
                         "published_at": "2026-02-01", "url": "https://example.com/w1", "country": "United Kingdom"}]},
                    "uk_sanctions_entities.json": {"records": [
                        {"uk_unique_id": "RUS0001", "name": "GARANTEX EUROPE OU", "name_type": "Primary Name",
                         "regime": "Russia", "date_designated": "01/01/2025"}]},
                    "fintrac_penalties_official.json": {"records": [
                        {"record_id": "f1", "entity_name": "Juba Express Inc", "published": "2026-01-02", "penalty_cad": 1000}]},
                    "us_fdic_institutions.json": {"records": [{"fdic_cert": "1", "institution": "West Shore Bank", "state": "MI"}]},
                    "global_enforcement.json": {"events": [
                        {"id": "x1", "institution": "Robin Example Person", "regulator": "FCA", "country_code": "GB"}]},
                }
                for name, obj in fixtures.items():
                    (path / name).write_text(json.dumps(obj), encoding="utf-8")
                g.generate()
                result = json.loads((path / "institution_intelligence.json").read_text(encoding="utf-8"))
                by_name = {x["name"]: x for x in result["institutions"]}
                juba = by_name["Juba Express Inc."]
                self.assertEqual(juba["counts"]["enforcement"], 1)
                self.assertEqual(juba["counts"]["headlines"], 1)
                self.assertEqual(juba["official_data"]["counts"]["fintrac_public_notices"], 1)
                head = next(r for r in juba["evidence"] if r["kind"] == "headline")
                self.assertEqual(head["role"], "official_entity_name_in_headline")
                garantex = next(x for x in result["institutions"] if "GARANTEX" in x["name"])
                self.assertEqual(garantex["counts"]["headlines"], 1)
                self.assertEqual(garantex["official_data"]["counts"]["sanctions_designations"], 1)
                west = next(x for x in result["institutions"] if x["id"] == "us-fdic-1")
                self.assertEqual(west["counts"]["headlines"], 0)
                self.assertFalse(any("Robin" in x["name"] for x in result["institutions"]))
                entities = json.loads((path / "headline_entities.json").read_text(encoding="utf-8"))
                self.assertIn("g1", entities["articles"])
            finally:
                g.DATA = original


if __name__ == "__main__":
    unittest.main()
