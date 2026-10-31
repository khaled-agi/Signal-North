"""Recovery of empty market scans without inventing 'no financial crime' claims."""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
import pycountry
from scripts.empty_country_recovery import choose_gap_batch, recovery_queries
from scripts.collect_world_news import markets, parse_feed, retained, search_queries
from scripts.world_country_lenses import country_profile, country_title_reference

NOW=datetime(2026,10,30,23,55,tzinfo=timezone.utc)
def feed(title,date="Fri, 30 Oct 2026 12:00:00 GMT"):
    return ('<rss version="2.0"><channel><item><title>'+title+'</title>'+
            '<link>https://news.google.com/rss/articles/recovery</link>'+
            '<pubDate>'+date+'</pubDate><source>Local publisher</source>'+
            '</item></channel></rss>').encode("utf-8")

class EmptyCountryRecoveryTests(unittest.TestCase):
    def test_priority_unattempted_then_empty_without_displacing_baseline(self):
        profiles=markets()
        selected=[p for p in profiles if p["code"] in ("ZA","FR")]
        statuses={
            "BO":{"state":"attempted_empty","attempted_at":"2026-10-30T12:00:00+00:00"},
            "MU":{"state":"attempted_empty","attempted_at":"2026-10-30T12:00:00+00:00"},
            "ZA":{"state":"attempted_empty","attempted_at":"2026-10-30T12:00:00+00:00"},
            "FR":{"state":"reporting_found","attempted_at":"2026-10-30T12:00:00+00:00"},
        }
        choices,cursor=choose_gap_batch(profiles,statuses,selected,0,8)
        self.assertEqual(len(choices),8)
        self.assertNotIn("FR",[p["code"] for p in choices])
        self.assertNotIn("ZA",[p["code"] for p in choices])
        self.assertNotIn("BO",[p["code"] for p in choices]) # Unscanned markets prioritized
        self.assertEqual(len({p["code"] for p in choices}),8)
        # All nonempty / previously attempted markets need no rescue.
        statuses={p["code"]:{"state":"reporting_found","attempted_at":"2026-10-30T12:00:00+00:00"} for p in profiles}
        none,unchanged=choose_gap_batch(profiles,statuses,[],6,8)
        self.assertEqual(none,[])
        self.assertEqual(unchanged,6)
        statuses["BO"]["state"]="attempted_empty"
        statuses["MU"]["state"]="attempted_empty"
        first,next_cursor=choose_gap_batch(profiles,statuses,[],0,1)
        second,_=choose_gap_batch(profiles,statuses,[],next_cursor,1)
        self.assertNotEqual(first[0]["code"],second[0]["code"])

    def test_country_specific_recovery_queries_are_bounded_and_local(self):
        by_code={p["code"]:p for p in markets()}
        self.assertEqual(len(recovery_queries(by_code["BO"])),2)
        self.assertIn("boliviana",recovery_queries(by_code["BO"])[1])
        self.assertIn("when:90d",recovery_queries(by_code["BO"])[1])
        self.assertIn("Maurice",recovery_queries(by_code["MU"])[1])
        self.assertIn("PNG",recovery_queries(by_code["PG"])[1])
        self.assertEqual(len(recovery_queries(by_code["AQ"])),1)
        self.assertEqual(len(search_queries(by_code["IN"]))>3,True)

    def test_true_country_demonym_accepts_article_but_no_incident_claim(self):
        for code,title in [
            ("BO","La policía boliviana recibe denuncias por estafas"),
            ("MU","Mauritian investors warned of investment fraud"),
            ("PG","PNG police warn of financial fraud"),
            ("BW","Botswana officials investigate scam"),
        ]:
            p=next(x for x in markets() if x["code"]==code)
            self.assertIsNotNone(country_title_reference(title,p))
            items=parse_feed(feed(title),p,recovery_queries(p)[0],NOW)
            self.assertEqual(len(items),1,code)
            self.assertEqual(items[0]["country_basis"],
                "country_explicitly_named_in_title_not_incident_location")
            self.assertEqual(items[0]["geolocation_accuracy"],"no_event_coordinates")

    def test_search_market_does_not_assign_unrelated_article(self):
        p=next(x for x in markets() if x["code"]=="BO")
        items=parse_feed(feed("Florida fraud case under investigation"),
                         p,recovery_queries(p)[0],NOW)
        self.assertEqual(items,[])

    def test_editorial_counterexamples_are_linked_but_not_automated_enforcement(self):
        path=Path(__file__).resolve().parents[1]/"data"/"world_coverage_counterexamples.json"
        examples=json.loads(path.read_text("utf-8"))["examples"]
        self.assertEqual({r["country_code"] for r in examples},{"BO","MU","PG","BW"})
        for row in examples:
            self.assertTrue(row["url"].startswith("https://"))
            self.assertTrue(row["evidence_status"])
            self.assertNotIn("penalty_amount",row)
            self.assertNotIn("map_latitude",row)
            self.assertTrue(row["published_at"].startswith("2026-"))

if __name__=="__main__":
    unittest.main()
