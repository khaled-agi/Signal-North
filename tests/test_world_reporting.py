"""Offline unit checks: every country is addressable, but not falsely ingested."""
import unittest
from datetime import datetime, timedelta, timezone
import pycountry
from scripts.collect_world_news import (
    markets, choose_batch, search_queries, feed_url, classify,
    parse_feed, retained, safe_link, MAX_AGE_DAYS,
)
from scripts.world_country_lenses import country_profile

NOW=datetime(2026,10,30,18,tzinfo=timezone.utc)

def rss(title="France: une escroquerie bancaire signalée", day="Fri, 30 Oct 2026 12:00:00 GMT"):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><item><title>{title}</title>
<link>https://news.google.com/rss/articles/test1</link><pubDate>{day}</pubDate>
<source>French financial reporting</source></item></channel></rss>""".encode()

class WorldCountryTest(unittest.TestCase):
    def test_every_iso_market_has_a_country_named_query(self):
        entries=markets()
        self.assertGreaterEqual(len(entries),240)
        self.assertEqual(len(entries),len({x["code"] for x in entries}))
        iso_codes={c.alpha_2 for c in pycountry.countries}
        self.assertEqual({x["code"] for x in entries},iso_codes|{"XK"})
        self.assertEqual(len(entries),len(iso_codes)+1)
        self.assertEqual(next(x for x in entries if x["code"]=="XK")["catalogue_type"],
                         "non_iso_user_assigned")
        for p in entries:
            self.assertIn(p["name"],search_queries(p)[0])

    def test_rotating_batches_exhaust_all_countries_without_duplicates(self):
        entries=markets()
        seen=set();cursor=0
        for _ in range(len(entries)//16+1):
            chunk,cursor=choose_batch(entries,cursor,16)
            for x in chunk:
                seen.add(x["code"])
        self.assertEqual(len(seen),len(entries))

    def test_kosovo_non_iso_discovery(self):
        xk=next(x for x in markets() if x["code"]=="XK")
        self.assertEqual(xk["name"],"Kosovo")
        self.assertEqual(xk["local_language"],"sq")
        self.assertIn("mashtrim",search_queries(xk)[1])
        self.assertIn("Kosovë",search_queries(xk)[1])
        self.assertEqual(xk["agency_directory"][0]["name"],"Central Bank of Kosovo")
        self.assertEqual(classify("Mashtrim bankar në Kosovë",xk),"Fraud and scam reporting")
        self.assertEqual(classify("Kosovo bank phishing scam",xk),"Cyber / account compromise")

    def test_localized_language_and_english_fallback(self):
        france=country_profile(pycountry.countries.get(alpha_2="FR"))
        saudi=country_profile(pycountry.countries.get(alpha_2="SA"))
        tanzania=country_profile(pycountry.countries.get(alpha_2="TZ"))
        angola=country_profile(pycountry.countries.get(alpha_2="AO"))
        self.assertIn("escroquerie",search_queries(france)[1])
        self.assertIn("احتيال",search_queries(saudi)[1])
        self.assertIn("utapeli",search_queries(tanzania)[1])
        self.assertEqual(angola["language_strategy"],"english_country_named_fallback")
        self.assertIn("gl=FR",feed_url(france,search_queries(france)[1]))
        self.assertIn("gl=US",feed_url(angola,search_queries(angola)[0]))

    def test_rss_discovery_has_no_claims_about_incident_location(self):
        fr=country_profile(pycountry.countries.get(alpha_2="FR"))
        leads=parse_feed(rss(),fr,search_queries(fr)[1],NOW)
        self.assertEqual(len(leads),1)
        lead=leads[0]
        self.assertEqual(lead["country_code"],"FR")
        self.assertEqual(lead["country_basis"],"search_market_only_not_confirmed_incident_location")
        self.assertEqual(lead["evidence_status"],"unverified_news_lead")
        self.assertEqual(lead["review_status"],"not_source_reviewed")
        self.assertEqual(lead["category"],"Fraud and scam reporting")
        self.assertNotIn("map_latitude",lead)
        self.assertNotIn("latitude",lead)

    def test_unrelated_headline_not_automatically_accepted(self):
        fr=country_profile(pycountry.countries.get(alpha_2="FR"))
        self.assertIsNone(classify("France signs a new renewable energy treaty",fr))
        self.assertEqual(parse_feed(rss("France opens new museum"),fr,"fraud",NOW),[])

    def test_old_and_unsafe_records_are_rejected(self):
        fr=country_profile(pycountry.countries.get(alpha_2="FR"))
        self.assertFalse(parse_feed(rss(day="Fri, 01 Jan 2021 12:00:00 GMT"),fr,"fraud",NOW))
        self.assertIsNone(safe_link("http://example.com/phish"))
        self.assertIsNone(safe_link("https://user:pass@example.com/secret"))
        self.assertEqual(retained([],NOW),[])

    def test_no_country_metadata_inferred_from_generic_headline(self):
        fr=country_profile(pycountry.countries.get(alpha_2="FR"))
        result=parse_feed(rss(title="Bank phishing attacks on mobile customers"),fr,"fraud",NOW)
        self.assertEqual(result[0]["country_code"],"FR")
        self.assertIn("search_market_only",result[0]["country_basis"])
        self.assertNotIn("verified_incident_location",result[0])

if __name__=="__main__":
    unittest.main()
