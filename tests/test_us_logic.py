"""Regression tests for all-state U.S. source collection and evidence provenance."""
import json
import unittest
from pathlib import Path
from scripts import collect_us as us

ROOT = Path(__file__).resolve().parents[1]

class USCoverageTests(unittest.TestCase):
    def test_all_states_and_dc_in_directory(self):
        self.assertEqual(len(us.STATES), 51)
        self.assertIn("DC", us.STATES)
        self.assertIn("AK", us.STATES)
        self.assertIn("HI", us.STATES)
        self.assertEqual(len({v["name"] for v in us.STATES.values()}), 51)
        for code, state in us.STATES.items():
            with self.subTest(code=code):
                self.assertTrue(-90 <= state["latitude"] <= 90)
                self.assertTrue(-180 <= state["longitude"] <= 180)

    def test_state_assignment_only_from_literal_headline(self):
        self.assertEqual(us.headline_state("Police report California bank fraud"), "CA")
        self.assertEqual(us.headline_state("Fraud charges filed in New York"), "NY")
        self.assertEqual(us.headline_state("Florida cryptocurrency scam leads to charges"), "FL")
        self.assertIsNone(us.headline_state("FBI says nationwide fraud cases rise"))
        self.assertEqual(us.headline_state("Bank in Washington DC reports fraud"), "DC")
        self.assertIsNone(us.headline_state("Atlanta company accused in wire fraud"))
        self.assertIsNone(us.headline_state("Fraud report published by Dallas media"))
        self.assertIsNone(us.headline_state("Georgia country cryptocurrency case"))
        self.assertEqual(us.headline_state("Bank fraud in Washington state"), "WA")

    def test_read_full_50_state_schema(self):
        s=json.loads((ROOT/"data"/"us_states.json").read_text("utf-8"))
        self.assertEqual(len(s["states"]), 51)
        self.assertIn("not incident locations",s["coordinate_role"])

    def test_original_ic3_state_data_is_complete_and_not_an_incidence_rate(self):
        report=json.loads((ROOT/"data"/"us_ic3_2025.json").read_text("utf-8"))
        self.assertEqual(report["year"],2025)
        self.assertEqual(report["source_url"],"https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf")
        self.assertEqual(set(report["states"]),set(us.STATES))
        self.assertEqual(len(report["states"]),51)
        self.assertEqual(report["states"]["CA"]["complaints"],116414)
        self.assertEqual(report["states"]["DC"]["complaints_per_100k"],448.8)
        self.assertEqual(report["national"]["all_complaints"],1008597)
        self.assertTrue(sum(x["complaints"] for x in report["states"].values()) <= report["national"]["all_complaints"])
        self.assertTrue(all(v["complaints"]>0 and v["reported_loss_usd"]>0 and v["complaints_per_100k"]>0 for v in report["states"].values()))
        self.assertIn("not verified unique crimes",report["definition"])

    def test_fincen_official_parsing_without_false_state_or_amount(self):
        html='''<table><tr><th>Enforcement</th><th>Date</th><th>Matter Number</th><th>Financial Institution</th></tr>
          <tr><td><a href="/system/files/2026-10/case.pdf">In the Matter of Example Bank</a></td>
          <td>10/13/2026</td><td>2026-03</td><td>Depository Institutions</td></tr></table>'''
        rows=us.fincen_actions(html)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["source"],"FinCEN")
        self.assertEqual(rows[0]["case_number"],"2026-03")
        self.assertEqual(rows[0]["published_at"],"2026-10-13")
        self.assertIsNone(rows[0]["state"])
        self.assertIsNone(rows[0]["financial_measure"])
        self.assertTrue(rows[0]["source_url"].startswith("https://www.fincen.gov/"))

    def test_cfpb_parser_requires_both_source_link_and_date(self):
        html='''<div class="case-entry"><p>Date filed: JAN 16, 2025</p>
           <h3><a href="/enforcement/actions/block-inc/">Block, Inc.</a></h3>
           <p>On January 16, 2025 the bureau issued an order.</p></div>
           <div><a href="/enforcement/actions/unverified-case/">Case without filing date</a></div>'''
        rows=us.cfpb_actions(html)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["institution"],"Block, Inc.")
        self.assertEqual(rows[0]["published_at"],"2025-01-16")
        self.assertEqual(rows[0]["status"],"CFPB-listed case; outcome not inferred")

    def test_news_feed_uses_title_not_search_term_for_state(self):
        xml='''<rss><channel><item><title>California investment fraud under investigation - Local News</title>
          <link>https://news.google.com/rss/articles/abc</link><pubDate>Fri, 23 Oct 2026 12:00:00 GMT</pubDate>
          <source>Local News</source></item>
          <item><title>Major FBI wire fraud investigation - National Desk</title>
          <link>https://news.google.com/rss/articles/def</link><pubDate>Fri, 23 Oct 2026 12:00:00 GMT</pubDate>
          <source>National Desk</source></item></channel></rss>'''
        rows=us.parse_feed(xml,"California")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["state"],"CA")
        self.assertIsNone(rows[1]["state"])
        self.assertEqual(rows[0]["evidence_level"],"unverified_syndicated_headline")
        self.assertEqual(rows[0]["review_status"],"requires_original_source_review")

    def test_seed_enforcement_records_are_source_linked_with_procedural_status(self):
        data=json.loads((ROOT/"data"/"us_enforcement.json").read_text("utf-8"))
        self.assertGreaterEqual(len(data["events"]),10)
        self.assertEqual({e["source"] for e in data["events"]},{"FinCEN","CFPB"})
        for e in data["events"]:
            self.assertTrue(e["source_url"].startswith("https://"))
            self.assertEqual(e["geographic_scope"],"federal")
            self.assertIsNone(e["state"])
            self.assertIsNone(e["financial_measure"])
        zelle=next(x for x in data["events"] if "Early Warning" in x["title"])
        self.assertIn("Dismissed with prejudice",zelle["status"])
        self.assertEqual(zelle["review_status"],"source_reviewed")

if __name__=="__main__":
    unittest.main()
