import json
import unittest
from pathlib import Path
import scripts.build_intelligence_graph as graph

DATA=Path(__file__).resolve().parents[1]/"data"/"obsi_firm_complaints.json"

class OfficialOBSIAnnualTests(unittest.TestCase):
 def test_2025_named_firms_and_report_totals(self):
  d=json.loads(DATA.read_text(encoding="utf-8"))
  rows=d["records"]
  self.assertEqual(len(rows),91)
  self.assertEqual(set(r["fiscal_year"] for r in rows),{2024,2025})
  for k,total in [("complaints_received",6329),("opened_cases",5375),("closed_cases",4373),("resolved_satisfaction",1051)]:
   self.assertEqual(sum(r[k] for r in rows if r["fiscal_year"]==2025),total)
  self.assertEqual(len({(r["institution"],r["fiscal_year"]) for r in rows}),len(rows))
  fy24=[r for r in rows if r["fiscal_year"]==2024]
  self.assertEqual(len(fy24),38)
  for metric,total in [("complaints_received",2527),("complaints_deemed_in_mandate",2445),("opened_cases",2504)]:
   self.assertEqual(sum(r[metric] for r in fy24),total)
  self.assertTrue(all(r["closed_cases"] is None for r in fy24))
  self.assertEqual(next(r for r in rows if r["institution"]=="Royal Bank of Canada" and r["fiscal_year"]==2025)["opened_cases"],1172)
  self.assertEqual(next(r for r in rows if r["institution"]=="TD Bank Group" and r["fiscal_year"]==2025)["opened_cases"],985)
  self.assertEqual(next(r for r in rows if r["institution"]=="Canadian Imperial Bank of Commerce" and r["fiscal_year"]==2025)["opened_cases"],1013)

 def test_canonical_names_keep_parent_and_subsidiary_distinct(self):
  self.assertEqual(graph.bank_key("TD Bank Group"),"td")
  self.assertEqual(graph.bank_key("Bank of Nova Scotia (The)"),"scotiabank")
  self.assertNotEqual(graph.bank_key("CIBC Mortgages Inc."),graph.bank_key("Canadian Imperial Bank of Commerce"))

if __name__=="__main__":unittest.main()
