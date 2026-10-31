import json
import unittest
from pathlib import Path
import scripts.build_intelligence_graph as graph

class CIRODealerCases(unittest.TestCase):
 def test_concluded_and_separate_entities(self):
  p=Path(__file__).resolve().parents[1]/"data/ciro_named_enforcement.json"
  rows=json.loads(p.read_text(encoding="utf-8"))["records"]
  self.assertEqual(len(rows),5)
  for r in rows:
   self.assertIn(r["status"],("concluded","concluded_settlement"))
   self.assertGreater(r["fine_cad"],0)
   self.assertGreaterEqual(r["costs_cad"],0)
   self.assertTrue(r["case_url"].startswith("https://www.ciro.ca/"))
  self.assertNotEqual(graph.bank_key("RBC Dominion Securities Inc."),graph.bank_key("Royal Bank of Canada"))
  self.assertNotEqual(graph.bank_key("National Bank Financial Inc."),graph.bank_key("National Bank of Canada"))
  self.assertNotEqual(graph.bank_key("Scotia Securities Inc."),graph.bank_key("Scotiabank"))

if __name__=="__main__":unittest.main()
