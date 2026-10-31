import unittest
from scripts.collect_obsi_public_reports import extract_documents
from scripts.collect_bcsc_rss import parse_feed
from scripts.collect_amf_open_data import parse_csv

class ProvincialAndObsiTests(unittest.TestCase):
 def test_obsi_catalog(self):
  html='<a href="https://media-001-ca.cdn.govstack.com/file/quarterly-2025.pdf">Q2 2025</a><a href="https://example.com/fake.pdf">Annual Report 2025</a>'
  rows=extract_documents(html,"https://www.obsi.ca/en/case-data-insights/quarterly-case-data/","quarterly")
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["report_year"],2025)
 def test_bcsc_discipline_vs_allegation(self):
  xml=b'<rss><channel><item><title>Discipline Order - Example Firm</title><link>https://www.bcsc.bc.ca/enforcement/decision</link><pubDate>Wed, 28 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
  x=parse_feed(xml,"disciplined_list")
  y=parse_feed(xml,"hearing_notices")
  self.assertEqual(x[0]["classification"],"official_disciplinary_publication")
  self.assertEqual(y[0]["classification"],"official_hearing_or_order_notice")
  self.assertNotEqual(x[0]["id"],y[0]["id"])
 def test_amf_csv(self):
  data="Nom de l'institution;Type;Année\\nCaisse Demo;Coopérative;2025\\n".replace("\\n","\n").encode()
  x=parse_csv(data) if False else None
  # A tiny resource deliberately fails because publication coverage is expected to be large.
  with self.assertRaises(ValueError):parse_csv(data)

if __name__=="__main__":unittest.main()
