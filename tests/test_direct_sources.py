"""Direct original-source RSS/index safety and source health tests."""
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock,patch
from scripts.direct_source_catalogue import SOURCES
from scripts.collect_direct_sources import (
 parse_rss,parse_index,valid_original,make_record,fetch_source,
 retained,relevant,MAX_AGE_DAYS
)

NOW=datetime(2026,10,30,20,30,tzinfo=timezone.utc)
def source(id):
 return next(s for s in SOURCES if s["id"]==id)

class DirectSourcesTests(unittest.TestCase):
 def test_all_first_party_sources_are_configured_without_false_coverage_claims(self):
  self.assertGreaterEqual(len(SOURCES),24)
  self.assertGreaterEqual(len({s["country"] for s in SOURCES}),15)
  kinds={s["kind"] for s in SOURCES}
  for name in ("local_newspaper","central_bank","securities_regulator",
               "financial_intelligence_unit","police","law_enforcement"):
   self.assertIn(name,kinds)
  self.assertEqual(len({s["id"] for s in SOURCES}),len(SOURCES))
  for s in SOURCES:
   self.assertEqual(s["url"].split("/")[0],"https:")
   self.assertIn(s["format"],("rss","index"))

 def test_rejects_google_news_mirrors_and_foreign_domains(self):
  s=source("in-sebi")
  self.assertTrue(valid_original("https://www.sebi.gov.in/orders/notice.html",s))
  for url in (
   "https://www.sebi.gov.in.evil.test/orders/item",
   "http://www.sebi.gov.in/orders/item",
   "https://news.google.com/rss/articles/item",
   "https://www.sebi.gov.in@evil.test/orders/item",
   "https://evil.test/?next=www.sebi.gov.in",
  ):
   self.assertIsNone(valid_original(url,s),url)

 def test_rss_filters_general_news_and_retains_real_publisher_country(self):
  s=source("ng-premiumtimes")
  xml='''<rss><channel>
  <item><title>Nigerian bank fraud investigators announce arrests</title>
  <link>https://www.premiumtimesng.com/news/12345.html</link>
  <pubDate>Fri, 30 Oct 2026 12:00:00 GMT</pubDate></item>
  <item><title>Weekend football schedule announced</title>
  <link>https://www.premiumtimesng.com/sports/football.html</link>
  <pubDate>Fri, 30 Oct 2026 11:00:00 GMT</pubDate></item>
  <item><title>Financial fraud reported overseas</title>
  <link>https://evil.test/other</link></item>
  </channel></rss>'''
  found=parse_rss(xml.encode(),s,NOW)
  self.assertEqual(len(found),1)
  row=found[0]
  self.assertEqual(row["publisher_country_code"],"NG")
  self.assertIsNone(row["country_code"])
  self.assertFalse(row["verified_final_enforcement"])
  self.assertEqual(row["date_basis"],"source_feed_publication_date")
  self.assertIn("not_event_location",row["country_basis"])

 def test_html_index_keeps_first_indexed_not_assumed_published_date(self):
  s=source("mu-bom")
  html='''<html><body><ul>
   <li><a href="/financial-stability/supervision/scam-alerts/social-media-scam">
      Scam Alert: fraudulent investment scheme on social media</a>29 August 2026</li>
   <li><a href="/financial-stability/supervision/scam-alerts/notices">Contact us</a></li>
   <li><a href="https://malicious.test/press/fraud">Financial fraud case</a></li>
  </ul></body></html>'''
  rows=parse_index(html.encode(),s,NOW)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["date_basis"],"first_indexed_not_publication_date")
  self.assertIsNone(rows[0]["published_at"])
  self.assertEqual(rows[0]["source_type"],"central_bank")
  self.assertEqual(rows[0]["source_domain"],"bom.mu")
  self.assertFalse(rows[0]["verified_final_enforcement"])

 def test_regulator_not_automatically_final_penalty(self):
  s=source("sg-mas")
  row=make_record("MAS issues provisional prohibition order against agent",
                  "https://www.mas.gov.sg/regulation/enforcement/2026/provisional-order",s,NOW)
  self.assertIsNotNone(row)
  self.assertFalse(row["verified_final_enforcement"])
  self.assertIsNone(row["country_code"])

 def test_parser_error_reported_not_fabricated_success(self):
  s=source("in-sebi")
  response=Mock()
  response.raise_for_status.return_value=None
  response.content=b"not rss"
  response.url=s["url"]
  response.headers={"content-type":"text/xml"}
  with patch("scripts.collect_direct_sources.requests.get",return_value=response):
   rows,health=fetch_source(s,NOW)
  self.assertEqual(rows,[])
  self.assertEqual(health["status"],"error")
  self.assertEqual(health["error_type"],"ParseError")

 def test_retention_preserves_first_seen_and_rejects_outside_catalog(self):
  s=source("ng-premiumtimes")
  rec=make_record("Bank fraud alert for Nigerian customers",
    "https://www.premiumtimesng.com/news/valid.html",s,NOW)
  self.assertEqual(len(retained([rec],NOW)),1)
  bad=dict(rec,id="bad",url="https://other.org/news/fraud")
  self.assertEqual(len(retained([bad],NOW)),0)

if __name__=="__main__": unittest.main()
