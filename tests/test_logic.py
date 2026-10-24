"""Regression tests for financial impact parsing and evidence link provenance."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collect import amount
from scripts import build_intelligence_graph as graph

class FinancialAmountTests(unittest.TestCase):
 def test_large_abbreviated_penalties(self):
  self.assertEqual(amount("$4.25M"),4250000)
  self.assertEqual(amount("$5.5M penalty"),5500000)
  self.assertEqual(amount("$6.5M"),6500000)
  self.assertEqual(amount("$4M"),4000000)
  self.assertEqual(amount("$600,000"),600000)
  self.assertEqual(amount("$1.2 billion"),1200000000)
  self.assertEqual(amount("No disclosed penalty"),None)

 def test_official_bank_aliases(self):
  self.assertEqual(graph.bank_key("The Toronto-Dominion Bank"),graph.bank_key("TD Bank"))
  self.assertEqual(graph.bank_key("Royal Bank of Canada"),graph.bank_key("RBC"))
  self.assertNotEqual(graph.bank_key("First Nations Bank of Canada"),graph.bank_key("National Bank of Canada"))
  self.assertNotEqual(graph.bank_key("Royal Bank of Canada"),graph.bank_key("Bank of Montreal"))

 def test_evidence_cannot_turn_customer_losses_into_bank_penalties(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)
   (p/"events.json").write_text(json.dumps({"events":[
     {"id":"e1","institution":"Royal Bank of Canada","published_at":"2024-04-11",
       "title":"Regulator order","penalty_cad":4250000,"source":"FCAC","source_url":"https://example.org/fcac"},
     {"id":"e2","institution":"First Nations Bank of Canada","published_at":"2024-05-11",
       "title":"Another order","penalty_cad":50000,"source":"FINTRAC","source_url":"https://example.org/fintrac"}]}))
   (p/"incidents.json").write_text(json.dumps({"incidents":[
     {"id":"c1","institution":"RBC","title":"Bank impersonation victim story",
       "reported_at":"2026-04-10","amount_cad":24000,"amount_type":"victim_reported_loss",
       "institution_role":"institution_impersonated","source_url":"https://example.org/report"}]}))
   (p/"article_index.json").write_text(json.dumps({"articles":[
     {"id":"a1","title":"Customer says fraudster impersonated RBC","published_at":"2026-05-20",
       "publisher":"Sample newsroom","url":"https://example.org/news",
       "banks_mentioned_in_headline":["RBC"],"amount_strings_in_headline":["$24,000"],
       "headline_case_candidate":True}]}))
   with patch.object(graph,"DATA",p):
    graph.generate()
   output=json.loads((p/"institution_intelligence.json").read_text())
   rbc=next(x for x in output["institutions"] if x["id"]=="rbc")
   first=next(x for x in output["institutions"] if x["id"]=="first-nations-bank")
   self.assertEqual(rbc["counts"],{"enforcement":1,"incidents":1,"headlines":1})
   self.assertEqual(rbc["annual_penalties_cad"]["2024"],4250000)
   self.assertEqual(first["counts"]["headlines"],0)
   case=next(x for x in rbc["evidence"] if x["kind"]=="incident")
   self.assertEqual(case["role"],"institution_impersonated")
   self.assertEqual(case["amount_type"],"victim_reported_loss")
   review=json.loads((p/"review_queue.json").read_text())
   self.assertEqual(review["items"][0]["review_status"],"unreviewed_headline_only")

if __name__=="__main__":
 unittest.main()
