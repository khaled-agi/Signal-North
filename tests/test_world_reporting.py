"""Offline unit checks: every country is addressable, but not falsely ingested."""
import unittest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pycountry
from scripts.collect_world_news import (
    markets, choose_batch, search_queries, feed_url, classify,
    parse_feed, retained, retained_unattributed, safe_link, query_edition, is_local_query, MAX_AGE_DAYS,
)
from scripts.world_country_lenses import country_profile, country_title_reference

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

    def test_published_registry_is_complete_and_geographically_honest(self):
        data=json.loads((Path(__file__).resolve().parents[1] /
                         "data" / "world_jurisdictions.json").read_text("utf-8"))
        entries=data["jurisdictions"]
        self.assertEqual(len(entries),250)
        self.assertEqual(data["iso_jurisdictions"],249)
        self.assertEqual(data["non_iso_research_jurisdictions"],1)
        self.assertEqual({x["code"] for x in entries},
                         {c.alpha_2 for c in pycountry.countries}|{"XK"})
        self.assertEqual({x["code"] for x in entries if x["map_latitude"] is None},
                         {"AQ","UM"})
        self.assertIsNotNone(next(x for x in entries if x["code"]=="PS")["map_latitude"])

    def test_kosovo_non_iso_discovery(self):
        xk=next(x for x in markets() if x["code"]=="XK")
        self.assertEqual(xk["name"],"Kosovo")
        self.assertEqual(xk["local_language"],"sq")
        self.assertIn("mashtrim",search_queries(xk)[3])
        self.assertIn("Kosovë",search_queries(xk)[3])
        self.assertEqual(xk["agency_directory"][0]["name"],"Central Bank of Kosovo")
        self.assertEqual(classify("Mashtrim bankar në Kosovë",xk),"Fraud and scam reporting")
        self.assertEqual(classify("Kosovo bank phishing scam",xk),"Cyber / account compromise")

    def test_localized_language_and_english_fallback(self):
        france=country_profile(pycountry.countries.get(alpha_2="FR"))
        saudi=country_profile(pycountry.countries.get(alpha_2="SA"))
        tanzania=country_profile(pycountry.countries.get(alpha_2="TZ"))
        bhutan=country_profile(pycountry.countries.get(alpha_2="BT"))
        angola=country_profile(pycountry.countries.get(alpha_2="AO"))
        self.assertIn("escroquerie",search_queries(france)[3])
        self.assertIn("احتيال",search_queries(saudi)[3])
        self.assertIn("utapeli",search_queries(tanzania)[3])
        self.assertEqual(bhutan["language_strategy"],"english_country_named_fallback")
        self.assertEqual(angola["local_language"],"pt")
        self.assertIn("gl=FR",feed_url(france,search_queries(france)[3]))
        self.assertIn("gl=US",feed_url(angola,search_queries(angola)[0]))
        self.assertIn("gl=BR",feed_url(angola,search_queries(angola)[3]))

    def test_local_language_query_expansion_and_correct_editions(self):
        profiles=markets()
        non_english=[p for p in profiles if p["local_term"] and p["local_language"]!="en"]
        self.assertGreaterEqual(len(non_english),130)
        self.assertEqual(len(profiles),250)
        for code,term in [("DZ","احتيال"),("SN","escroquerie"),
                           ("DO","estafa"),("AO","burla"),("SE","bedrägeri"),
                           ("KZ","алаяқтық"),("MM","လိမ်လည်မှု"),
                           ("RW","uburiganya")]:
            p=next(x for x in profiles if x["code"]==code)
            self.assertIn(term,search_queries(p)[3])
            self.assertTrue(is_local_query(p,search_queries(p)[3]))
            self.assertIsNotNone(classify(term+" "+p["local_country_term"],p))
        france=next(x for x in profiles if x["code"]=="FR")
        jordan=next(x for x in profiles if x["code"]=="JO")
        self.assertEqual(query_edition(france,search_queries(france)[0])[0][1],"US")
        self.assertEqual(query_edition(france,search_queries(france)[3])[0][1],"FR")
        self.assertEqual(query_edition(jordan,search_queries(jordan)[3])[0][1],"SA")
        self.assertEqual(query_edition(jordan,search_queries(jordan)[3])[1],
                         "language_proxy_edition")
        self.assertEqual(query_edition(jordan,search_queries(jordan)[0])[0][1],"US")

    def test_unlocated_local_headline_is_not_mapped_or_assigned(self):
        france=country_profile(pycountry.countries.get(alpha_2="FR"))
        title="Une escroquerie bancaire frappe des clients"
        local=search_queries(france)[3]
        unmatched=[]
        located=parse_feed(rss(title=title),france,local,NOW,unmatched)
        self.assertEqual(located,[])
        self.assertEqual(len(unmatched),1)
        item=unmatched[0]
        self.assertIsNone(item["country_code"])
        self.assertEqual(item["search_market_code"],"FR")
        self.assertEqual(item["query_language"],"fr")
        self.assertEqual(item["evidence_status"],"unattributed_local_language_search_candidate")
        self.assertNotIn("map_latitude",item)
        self.assertNotIn("latitude",item)
        self.assertEqual(len(retained_unattributed(unmatched,NOW)),1)
        self.assertEqual(retained(unmatched,NOW),[])
        # Even a local edition may return unrelated foreign headlines. Neither
        # English nor local query results can become an invented map location.
        jordan=country_profile(pycountry.countries.get(alpha_2="JO"))
        not_jordan=[]
        parse_feed(rss(title="Orlando woman targeted by scam"),
                   jordan,search_queries(jordan)[3],NOW,not_jordan)
        self.assertEqual(not_jordan,[])
        bad=dict(item,country_code="FR")
        self.assertEqual(retained_unattributed([bad],NOW),[])

    def test_rss_discovery_has_no_claims_about_incident_location(self):
        fr=country_profile(pycountry.countries.get(alpha_2="FR"))
        leads=parse_feed(rss(),fr,search_queries(fr)[3],NOW)
        self.assertEqual(len(leads),1)
        lead=leads[0]
        self.assertEqual(lead["country_code"],"FR")
        self.assertEqual(lead["country_basis"],"country_explicitly_named_in_title_not_incident_location")
        self.assertEqual(lead["country_reference_term"],"France")
        self.assertEqual(lead["evidence_status"],"unverified_news_lead")
        self.assertEqual(lead["review_status"],"not_source_reviewed")
        self.assertEqual(lead["category"],"Fraud and scam reporting")
        self.assertNotIn("map_latitude",lead)
        self.assertNotIn("latitude",lead)

    def test_worldwide_enforcement_reporting_is_not_verified_order(self):
        france=country_profile(pycountry.countries.get(alpha_2="FR"))
        self.assertEqual(classify("French bank fined by financial regulator",france),
                         "Reported financial regulatory enforcement (unverified)")
        self.assertEqual(classify("Banque française reçoit une amende",france),
                         "Reported financial regulatory enforcement (unverified)")
        self.assertIsNone(classify("Food safety regulator fines restaurant",france))
        self.assertEqual(len(search_queries(france)),4)
        record=parse_feed(rss("French bank fined by financial regulator"),
                          france,search_queries(france)[2],NOW)[0]
        self.assertEqual(record["evidence_status"],"unverified_news_lead")
        self.assertEqual(record["search_language"],"en")
        self.assertEqual(record["category"],"Reported financial regulatory enforcement (unverified)")
        self.assertEqual(record["country_basis"],"country_explicitly_named_in_title_not_incident_location")

    def test_jordan_search_excludes_unrelated_international_headlines(self):
        jordan=country_profile(pycountry.countries.get(alpha_2="JO"))
        titles=[
            "Orlando man arrested in fraud targeting elderly woman",
            "Former RMW worker charged with bribery scam - Boston Globe",
            "Israeli police find no evidence backing election fraud claims",
            "RCMP investigating Alberta health spending with possible money laundering",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertIsNone(country_title_reference(title,jordan))
                self.assertEqual(parse_feed(rss(title=title),jordan,
                           search_queries(jordan)[0],NOW),[])
        match=parse_feed(rss(title="Jordanian banks warn of phishing scams"),
                         jordan,search_queries(jordan)[0],NOW)
        self.assertEqual(len(match),1)
        self.assertEqual(match[0]["country_reference_status"],
                         "country_name_in_headline_not_incident_location")

    def test_old_search_market_records_are_revalidated(self):
        jordan=country_profile(pycountry.countries.get(alpha_2="JO"))
        valid=parse_feed(rss(title="Jordanian banks warn about fraud"),
                         jordan,search_queries(jordan)[0],NOW)[0]
        old=dict(valid,id="old-jordan-wrong",title="Orlando fraud case",
                 country_basis="search_market_only_not_confirmed_incident_location")
        kept=retained([valid,old],NOW)
        self.assertEqual(len(kept),1)
        self.assertEqual(kept[0]["id"],valid["id"])

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
        self.assertEqual(result,[], "A search market is not evidence of country relevance")

if __name__=="__main__":
    unittest.main()
