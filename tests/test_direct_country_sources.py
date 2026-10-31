import unittest,json
from pathlib import Path
from datetime import datetime,timezone
from scripts.collect_direct_country_sources import items,legal_link,catalog,ALLOW_KINDS

class TestDirectSources(unittest.TestCase):
 def test_catalog_strict_original_domains_and_source_kinds(self):
  sources=catalog()
  self.assertGreaterEqual(len(sources),5)
  self.assertIn("newspaper",{s["kind"] for s in sources})
  self.assertIn("regulator",{s["kind"] for s in sources})
  for s in sources:
   self.assertIn(s["kind"],ALLOW_KINDS)
   self.assertTrue(legal_link(s["feed_url"],s["domain"]))
  self.assertIsNone(legal_link("https://sebi.gov.in.attacker.example/rss","sebi.gov.in"))
  self.assertIsNone(legal_link("http://www.sebi.gov.in/sebirss.xml","sebi.gov.in"))

 def test_rss_original_source_news_not_automatically_enforcement(self):
  source={"id":"in-sebi","country_code":"IN","name":"SEBI","kind":"regulator",
          "domain":"sebi.gov.in","feed_url":"https://www.sebi.gov.in/sebirss.xml"}
  rss=b"""<rss><channel><item><title>SEBI imposes penalty on investment firm</title>
  <link>https://www.sebi.gov.in/enforcement/some-order.html</link>
  <pubDate>Fri, 30 Oct 2026 11:00:00 GMT</pubDate></item>
  <item><title>SEBI imposes fine</title>
  <link>https://sebi.gov.in.attacker.example/fine</link>
  <pubDate>Fri, 30 Oct 2026 11:00:00 GMT</pubDate></item>
  </channel></rss>"""
  records=items(rss,source,datetime(2026,10,30,20,tzinfo=timezone.utc))
  self.assertEqual(len(records),1)
  r=records[0]
  self.assertEqual(r["source_kind"],"regulator")
  self.assertEqual(r["evidence_status"],"direct_publisher_publication_unverified")
  self.assertEqual(r["legal_status"],"not_assessed_not_final_enforcement")
  self.assertEqual(r["country_basis"],"publisher_source_market_not_verified_incident_location")
  self.assertNotIn("map_latitude",r)

 def test_atom_entry_and_filtered_unrelated_news(self):
  source={"id":"gh-citi-business","country_code":"GH","name":"Citi","kind":"newspaper",
          "domain":"citinewsroom.com","feed_url":"https://citinewsroom.com/rss/business.rss"}
  atom=b"""<feed xmlns="http://www.w3.org/2005/Atom">
    <entry><title>Banking scam victims warn investors</title>
    <link href="https://citinewsroom.com/2026/10/bank-scam/"/>
    <updated>2026-10-30T11:00:00Z</updated></entry>
    <entry><title>Football squad prepares for match</title>
    <link href="https://citinewsroom.com/sports/football"/>
    <updated>2026-10-30T11:00:00Z</updated></entry>
    </feed>"""
  records=items(atom,source,datetime(2026,10,30,20,tzinfo=timezone.utc))
  self.assertEqual(len(records),1)
  self.assertEqual(records[0]["source_kind"],"newspaper")
if __name__=="__main__":unittest.main()
