import json
import tempfile
import unittest
from pathlib import Path
import scripts.build_intelligence_graph as g

class InstitutionJoinTest(unittest.TestCase):
 def test_osfi_parenthetical_names_resolve(self):
  self.assertEqual(g.bank_key("Toronto-Dominion Bank (The)"),"td")
  self.assertEqual(g.bank_key("Bank of Nova Scotia (The)"),"scotiabank")

 def test_source_specific_data_joins_without_inflating_regulator_event_count(self):
  original=g.DATA
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)
   try:
    g.DATA=path
    fixtures={
     "events.json":{"events":[]},
     "incidents.json":{"incidents":[]},
     "reporting_groups.json":{"groups":[]},
     "bank_complaint_disclosures.json":{"records":[{"id":"td-2025","institution":"Toronto-Dominion Bank","year":2025,"metric_value":5403,"source_url":"https://td.com/report"}]},
     "osfi_institutions.json":{"records":[{"fields":{"Company Name":"The Toronto-Dominion Bank","FI Group Name":"Domestic Banks","FI Industry Name":"Canadian Banks"}}]},
     "fintrac_penalties_official.json":{"records":[{"record_id":"f-1","entity_name":"Toronto-Dominion Bank","published":"2025-03-01","penalty_cad":3000,"source_url":"https://fintrac-canafe.canada.ca/pen/4-eng"}]},
     "canadian_enforcement_verified.json":{"records":[{"name":"Toronto-Dominion Bank","agency":"FCAC","published":"2025-04-01","penalty_cad":2500,"url":"https://canada.ca/fcac"}]},
     "obsi_annual_banking.json":{"rows":[{"year":2025,"banking_cases_opened":5438}]},
    }
    for name,obj in fixtures.items():
     (path/name).write_text(json.dumps(obj),encoding="utf-8")
    g.generate()
    result=json.loads((path/"institution_intelligence.json").read_text(encoding="utf-8"))
    td=next(x for x in result["institutions"] if x["id"]=="td")
    self.assertEqual(td["counts"]["enforcement"],0)
    self.assertEqual(td["official_data"]["counts"]["fintrac_public_notices"],1)
    self.assertEqual(td["official_data"]["counts"]["fcac_index_notices"],1)
    self.assertEqual(td["official_data"]["counts"]["bank_disclosure_years"],1)
    self.assertEqual(td["official_data"]["osfi"]["name"],"The Toronto-Dominion Bank")
    self.assertEqual(len(result["sector_context"]["obsi_banking"]),1)
    self.assertEqual(result["source_counts"]["bank_disclosure_records"],1)
   finally:g.DATA=original

if __name__=="__main__":
 unittest.main()
