"""Regression tests for financial impact parsing and evidence link provenance."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collect import amount
from scripts import build_intelligence_graph as graph
from scripts import build_theme_trends as theme_trends
from scripts import build_story_groups as reporting
from scripts import build_related_reporting as related

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

class HistoricalThemeTests(unittest.TestCase):
 def test_yearly_headline_topics_not_incidents(self):
  documents=[
   {"id":"a","title":"Crypto investment scam reported in Toronto","published_at":"2021-05-01","publisher":"Original source"},
   {"id":"b","title":"Bank impersonation phishing scam in Ontario","published_at":"2024-09-01","publisher":"Other source"},
   {"id":"c","title":"Casinos investigated over money laundering","published_at":"2026-03-10","publisher":"Regulatory release"},
  ]
  data=theme_trends.classify_articles(documents)
  self.assertEqual(data["articles_by_year"]["2021"],1)
  self.assertEqual(data["articles_by_year"]["2024"],1)
  self.assertEqual(data["articles_by_year"]["2026"],1)
  lookup={x["name"]:x for x in data["themes"]}
  self.assertEqual(lookup["Investment & crypto scams"]["year_counts"]["2021"],1)
  self.assertEqual(lookup["Bank impersonation & phishing"]["year_counts"]["2024"],1)
  self.assertEqual(lookup["Gambling, gaming & casino"]["year_counts"]["2026"],1)
  self.assertEqual(lookup["Money mules & laundering"]["year_counts"]["2026"],1)

 def test_platform_mentions_are_not_bank_penalties(self):
  self.assertNotEqual(graph.bank_key("Wealthsimple"),graph.bank_key("Wealthsimple Investments Inc."))
  self.assertNotEqual(graph.bank_key("Wealthsimple"),graph.bank_key("Royal Bank of Canada"))
  self.assertNotEqual(graph.bank_key("Binance"),graph.bank_key("BCLC"))

class GroupedReportingTests(unittest.TestCase):
 def example(self,title,date="2025-04-11",url="https://source.example/a",**extra):
  return {"id":url.replace("/","_"),"title":title,"published_at":date,
    "publisher":"Sample press","url":url,
    "article_links":[{"title":title,"url":url,"published_at":date,"publisher":"Sample press"}],**extra}

 def test_group_near_identical_reports_and_preserve_headline_variants(self):
  docs=[
   self.example("Toronto investor loses $50,000 in elaborate crypto romance scam involving fake trading app",url="https://a.example/1"),
   self.example("Toronto investor loses $50,000 in elaborate crypto romance scam involving a fake trading app",date="2025-04-13",url="https://b.example/2"),
   self.example("Toronto investor loses $50,000 in elaborate crypto romance scam involving fake trading app",date="2025-04-12",url="https://c.example/3"),
  ]
  grouped=reporting.display_groups(docs)
  self.assertEqual(len(grouped),1)
  self.assertEqual(grouped[0]["underlying_headline_count"],3)
  self.assertEqual(grouped[0]["source_count"],3)
  self.assertEqual(grouped[0]["variation_count"],2)
  self.assertEqual(len(grouped[0]["headline_variations"]),3)
  self.assertTrue(all(v["url"].startswith("https://") for v in grouped[0]["headline_variations"]))

 def test_do_not_merge_materially_distinct_reporting(self):
  base="Toronto investor loses $50,000 in elaborate crypto romance scam involving fake trading app"
  rows=[
   self.example(base,url="https://a.example/1"),
   self.example("Toronto investor loses $500,000 in elaborate crypto romance scam involving fake trading app",url="https://a.example/2"),
   self.example(base,date="2025-08-11",url="https://a.example/3"),
   self.example(base,url="https://a.example/4",map_latitude=49.2,map_longitude=-123.2),
   self.example(base,url="https://a.example/5",map_latitude=45.5,map_longitude=-73.5),
  ]
  groups=reporting.display_groups(rows)
  self.assertGreaterEqual(len(groups),4)
  self.assertEqual(sum(x["underlying_headline_count"] for x in groups),len(rows))

 def test_geographic_relevance_never_uses_publisher_location(self):
  foreign=self.example("Argentinian crypto investor exposes alleged scam in Buenos Aires",url="https://yahoo.ca/report")
  local=self.example("Toronto crypto investor reports account takeover",url="https://world.example/report")
  uncertain=self.example("Investment platform issues new global market security warning",url="https://canadapublisher.ca/report")
  self.assertEqual(reporting.geographic_relevance(foreign)[0],"international_context_explicit")
  self.assertEqual(reporting.geographic_relevance(local)[0],"canadian_location_or_reference")
  self.assertEqual(reporting.geographic_relevance(uncertain)[0],"geography_unresolved")

 def test_group_is_discovery_not_verified_incident(self):
  row=self.example("Winnipeg woman reports alleged online investment account scam while police investigate",url="https://a.example/1")
  group=reporting.display_groups([row])[0]
  self.assertEqual(group["evidence_status"],"unverified_grouped_reporting")
  self.assertIn("not independently verified",group["grouping_disclaimer"])
  self.assertEqual(group["article_ids"],[row["id"]])

class ReviewedCaseNarrativeTests(unittest.TestCase):
 def test_reviewed_case_sequencing_is_attributed_and_nonempty(self):
  # Schema guard, not independent verification of the underlying claims.
  record=json.loads((Path(__file__).resolve().parents[1]/"data"/"incidents.json").read_text("utf-8"))
  incidents=record["incidents"]
  self.assertGreaterEqual(len(incidents),6)
  self.assertEqual(len({x["id"] for x in incidents}),len(incidents))
  for case in incidents:
   with self.subTest(case=case["id"]):
    self.assertTrue(case["source_url"].startswith("https://"))
    self.assertIn(case["amount_type"],("victim_reported_loss","unauthorized_credit_exposure","recovered_amount"))
    self.assertIn(case["institution_role"],(
     "customer_financial_institution","institution_impersonated",
     "bank_not_identified","unnamed_financial_institution_assisted_recovery"))
    stages=case["investigation"]["stages"]
    questions=case["investigation"]["questions"]
    self.assertGreaterEqual(len(stages),2)
    self.assertGreaterEqual(len(questions),2)
    self.assertTrue(all(len(stage)==2 and all(isinstance(s,str) and s.strip() for s in stage) for stage in stages))
    self.assertTrue(all(isinstance(q,str) and q.strip().endswith("?") for q in questions))


class SuggestedRelationshipTests(unittest.TestCase):
 def sample(self,title,name,date,ident):
  return {"id":ident,"title":title,"published_at":date,
   "banks_mentioned_in_headline":[name] if name else [],
   "fraud_themes":["Investment & crypto scams"],"source_url":"https://example.org/"+ident}

 def test_shared_clues_produce_an_unverified_link(self):
  a=self.sample("Toronto investment crypto platform warning after customer loses funds with impersonation", "Wealthsimple", "2025-05-02","a")
  b=self.sample("Toronto investment crypto platform warning after customer loses money with impersonation", "Wealthsimple", "2025-05-04","b")
  result=related.assess(a,b)
  self.assertIsNotNone(result)
  links,_=related.generate([a,b])
  self.assertEqual(links["a"][0]["group_id"],"b")
  self.assertEqual(links["a"][0]["relationship_status"],"unverified_research_lead")

 def test_unrelated_cases_never_become_matches(self):
  a=self.sample("Toronto fake investment app complaint by customers", "Wealthsimple","2024-01-01","a")
  b=self.sample("Toronto fake investment app complaint by customers", "Binance","2026-01-01","b")
  self.assertIsNone(related.assess(a,b))

if __name__=="__main__":
 unittest.main()
