import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import scripts.collect_us_fdic as fdic
import scripts.collect_us_ncua as ncua
import scripts.build_intelligence_graph as graph

class USInstitutionIngestionTests(unittest.TestCase):
 def test_fdic_api_pagination_and_certificate_identity(self):
  class Session:
   def get(self,url,params=None,headers=None,timeout=None):
    offset=int(params["offset"])
    values=[{"data":{"CERT":i+1,"NAME":"Demo Bank "+str(i+1),"CITY":"Springfield","STALP":"IL","ACTIVE":1}}
            for i in range(offset,min(offset+1000,3100))]
    class Response:
     status_code=200
     content=b"fake"
     def raise_for_status(self):pass
     def json(self):return {"data":values,"meta":{"total":3100}}
    return Response()
  with patch.dict(fdic.MIN_ROWS,{"institutions":3000}):
   rows=fdic.collect(Session(),"institutions")
  self.assertEqual(len(rows),3100)
  self.assertEqual(rows[0]["fdic_cert"],"1")
  self.assertEqual(rows[-1]["fdic_cert"],"3100")

 def test_fdic_failure_is_not_enforcement(self):
  value=fdic.normalize({"data":{"CERT":123,"NAME":"Example Failed Bank",
                  "FAILDATE":"2026-01-01","RESTYPE":"Failure","CITY":"Town",
                  "PSTALP":"NY","QBFASSET":456}},"failures")
  self.assertEqual(value["fdic_cert"],"123")
  self.assertEqual(value["source_kind"],"fdic_failure_or_assistance")
  self.assertIn("NOT a financial-crime finding",value["classification_note"])

 def test_fdic_legacy_failure_without_certificate_preserves_record_id(self):
  row=fdic.normalize({"data":{"ID":9876,"CERT":None,"NAME":"Legacy Assisted Bank","FAILDATE":"1987-01-01","CITY":"Town"}},"failures")
  self.assertEqual(row["fdic_event_id"],"9876")
  self.assertIsNone(row["fdic_cert"])
  self.assertEqual(row["institution"],"Legacy Assisted Bank")

 def test_ncua_zip_foicu_parsed_by_charter(self):
  rows="CU_NUMBER,CU_NAME,CITY,STATE,CU_TYPE,RSSD\n"
  rows+="\n".join(f"{i},Demo Credit Union {i},Chicago,IL,1,{i+120}" for i in range(1,3701))
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,"w") as z:
   z.writestr("FOICU.txt",rows)
  data=ncua.parse_roster(raw.getvalue(),2026,6)
  self.assertEqual(len(data),3700)
  self.assertEqual(data[0]["ncua_charter"],"1")
  self.assertEqual(data[0]["cycle"],"2026-06")

 def test_ncua_discovery_uses_latest_official_final_quarter(self):
  html='<a href="/files/publications/analysis/call-report-data-2025-12.zip">Older</a><a href="/files/publications/analysis/call-report-data-2026-06.zip">Latest</a>'
  self.assertEqual(ncua.find_latest_zip(html)[:2],(2026,6))

 def test_graph_us_identifiers_do_not_merge_with_canadian_names(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   fixture={
    "events.json":{"events":[]},"incidents.json":{"incidents":[]},
    "reporting_groups.json":{"groups":[]},
    "osfi_institutions.json":{"records":[{"fields":{"Company Name":"Demo Bank"}}]},
    "us_fdic_institutions.json":{"records":[{"fdic_cert":"123","institution":"Demo Bank","state":"IL","city":"Chicago","active":True}]},
    "us_fdic_failures.json":{"records":[{"fdic_cert":"777","institution":"Failed Demo Bank","failure_date":"2023-03-01","resolution_type":"Failure","state":"IL"}]},
    "us_ncua_credit_unions.json":{"records":[{"ncua_charter":"456","institution":"Demo Bank","state":"IL","city":"Chicago","cycle":"2026-06"}]},
   }
   for name,obj in fixture.items():(root/name).write_text(json.dumps(obj))
   old=graph.DATA
   try:
    graph.DATA=root
    graph.generate()
    d=json.loads((root/"institution_intelligence.json").read_text("utf-8"))
   finally:graph.DATA=old
   ids={r["id"]:r for r in d["institutions"]}
   self.assertIn("us-fdic-123",ids)
   self.assertIn("us-fdic-777",ids)
   self.assertIn("us-ncua-456",ids)
   self.assertEqual(ids["us-fdic-777"]["counts"]["enforcement"],0)
   self.assertEqual(ids["us-fdic-777"]["official_data"]["counts"]["fdic_failures"],1)
   self.assertNotEqual(ids["us-fdic-123"]["id"],ids["us-ncua-456"]["id"])
   self.assertEqual(d["source_counts"]["us_fdic_active_entities"],1)
   self.assertEqual(d["source_counts"]["us_ncua_credit_union_entities"],1)

if __name__=="__main__":unittest.main()
