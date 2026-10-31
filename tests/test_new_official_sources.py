import unittest
from scripts.collect_us_occ_actions import normalize, parse_amount, to_date
from scripts.collect_us_ofac import parse as ofac_parse
from scripts.collect_us_sec_litigation import from_rss, from_html

class NewOfficialSignalTests(unittest.TestCase):
 def test_occ_individual_vs_bank_action_and_subjects(self):
  row={"Institution":"PNC Bank, National Association","CharterNumber":"1316",
       "Individual":"Denton Douglas","TypeCode":"CMP",
       "TypeDescription":"Civil Money Penalty (CMP)","Amount":"35,000.00",
       "StartDate":"01/08/2021","StartDocuments":["2021-008"],
       "TerminationDate":"","DocketNumber":"AA-EC-20-39",
       "SubjectMatters":["BSA/AML","Fraud/Forgery","Insider Issues"]}
  item=normalize(row)
  self.assertTrue(item["subject_is_individual"])
  self.assertEqual(item["amount_usd"],35000)
  self.assertEqual(item["occ_charter"],"1316")
  self.assertEqual(item["start_date"],"2021-01-08")
  self.assertIn("BSA/AML",item["subject_matters"])
  self.assertEqual(parse_amount("See Order"),None)
  r=normalize({**row,"Individual":"","TypeCode":"C&D"})
  self.assertFalse(r["subject_is_individual"])
  self.assertNotEqual(item["id"],r["id"])

 def test_ofac_sdn_12_columns_and_type_distinction(self):
  lines=[
   '1234,"DEMO HOLDINGS","-0-","[SDGT] [IRAN]","-0-","-0-","-0-","-0-","-0-","-0-","-0-","-0-"',
   '1235,"DEMO INDIVIDUAL","individual","[SDGT]","-0-","-0-","-0-","-0-","-0-","-0-","-0-","-0-"',
   '1236,"TEST VESSEL","vessel","[IRAN]","-0-","-0-","-0-","-0-","-0-","-0-","-0-","-0-"',
  ]
  with self.assertRaises(ValueError):
   ofac_parse(("\n".join(lines)+"\n").encode())
  # Parsing the actual file has a high minimum to prevent publishing a sample.
  rows,stats=ofac_parse(("\n".join(lines)+"\n").encode(),minimum=1)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["sanctions_programs"],["SDGT","IRAN"])
  self.assertEqual(stats["excluded_types"]["individual"],1)
  self.assertEqual(stats["excluded_types"]["vessel"],1)

 def test_sec_rss_official_host_only(self):
  rss=b'''<rss><channel>
    <item><title>Example SEC Litigation</title><link>https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26600</link><pubDate>Sat, 31 Oct 2026 10:00:00 GMT</pubDate></item>
    <item><title>Fake SEC Notice</title><link>https://sec.gov.evil.example/notice</link></item>
   </channel></rss>'''
  rows=from_rss(rss)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["legal_status"],"court_litigation_publication_unreviewed")
  self.assertEqual(rows[0]["publication_date"],"2026-10-31")

 def test_sec_html_fallback(self):
  html='<a href="/enforcement-litigation/litigation-releases/lr-26600">Example Entity</a><a href="https://fake.example/litigation/lr-1">Fake</a>'
  rows=from_html(html)
  self.assertEqual(len(rows),1)

if __name__=="__main__":unittest.main()
