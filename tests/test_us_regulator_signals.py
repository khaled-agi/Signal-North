import unittest
import scripts.collect_us_regulatory_signals as signals

class RegulatorPublicationTests(unittest.TestCase):
 def test_respect_official_domains(self):
  source={"agency":"Federal Reserve","allowed":"federalreserve.gov","kind":"enforcement_publication"}
  xml=b'''<?xml version="1.0"?><rss version="2.0"><channel>
  <item><title>Board announces enforcement action</title><link>https://www.federalreserve.gov/newsevents/pressreleases/enforcement20261031a.htm</link><pubDate>Sat, 31 Oct 2026 12:00:00 GMT</pubDate></item>
  <item><title>Impersonated source</title><link>https://federalreserve.gov.evil.example/notice</link></item>
  </channel></rss>'''
  result=signals.from_feed(xml,source)
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]["evidence_status"],"official_publication_unreviewed")
  self.assertEqual(result[0]["publication_date"],"2026-10-31")

 def test_occ_filters_other_news(self):
  source={"agency":"OCC","allowed":"occ.gov","kind":"enforcement_publication"}
  xml=b'''<rss><channel>
  <item><title>OCC Releases Interest Rate Report</title><link>https://www.occ.gov/news/2026/news-11.html</link></item>
  <item><title>OCC Announces Enforcement Actions for October</title><link>https://www.occ.gov/news/2026/news-12.html</link></item>
  </channel></rss>'''
  result=signals.from_feed(xml,source)
  self.assertEqual(len(result),1)
  self.assertIn("Enforcement",result[0]["title"])

 def test_ncua_official_enforcement_and_closure_only(self):
  html='''<a href="/newsroom/press-release/2026/ncua-prohibits-individual">NCUA Prohibits Individual</a>
  <a href="/newsroom/press-release/2026/grant">NCUA Awards New Grant</a>
  <a href="https://ncua.gov.attacker.example/newsroom/press-release/fraud">Fraud impersonation</a>'''
  x=signals.from_ncua(html,{"url":"https://ncua.gov/news/press-releases"})
  self.assertEqual(len(x),1)
  self.assertEqual(x[0]["agency"],"NCUA")

if __name__=="__main__":unittest.main()
