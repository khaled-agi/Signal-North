"""CFPB structured public complaints: allowlist, provenance and honest source health."""
import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock,patch
from scripts import collect_cfpb_complaints as c

NOW=datetime(2026,10,30,12,0,tzinfo=timezone.utc)
def hit(cid="12345678",date="2026-10-25"):
 return {"_id":cid,"_source":{
  "complaint_id":int(cid),"date_received":date,"company":"Example Bank Ltd.",
  "product":"Checking or savings account","sub_product":"Checking account",
  "issue":"Managing an account","sub_issue":"Problem with a transaction",
  "state":"NY","company_response":"Closed with explanation","timely":"Yes",
  "complaint_what_happened":"PRIVATE narrative must never be persisted",
  "zip_code":"10001","consumer_narrative":"PRIVATE personal story",
  "submitted_via":"Web","tags":"Older American",
  "consumer_consent_provided":"Consent provided",
 }}
class CFPBCollectorTests(unittest.TestCase):
 def test_only_public_categories_not_narratives_or_zipcodes(self):
  x=c.record(hit())
  self.assertEqual(x["id"],"12345678")
  self.assertEqual(x["state"],"NY")
  self.assertEqual(x["source_url"],c.BASE+"12345678")
  self.assertEqual(x["evidence_status"],"published_consumer_complaint_not_verified")
  self.assertNotIn("complaint_what_happened",x)
  self.assertNotIn("zip_code",x)
  self.assertNotIn("consumer_narrative",x)
  self.assertNotIn("submitted_via",x)
  self.assertNotIn("tags",x)
  self.assertNotIn("consumer_consent_provided",x)
  self.assertNotIn("PRIVATE",json.dumps(x))
  self.assertEqual(x["geography_basis"],"consumer_reported_state_not_incident_location")

 def test_search_result_shape_and_exact_total_only(self):
  body={"hits":{"hits":[hit(),hit("12345679")],
                "total":{"value":800,"relation":"eq"}}}
  rows,total=c.unpack(body)
  self.assertEqual(len(rows),2)
  self.assertEqual(total,800)
  body["hits"]["total"]["relation"]="gte"
  self.assertIsNone(c.unpack(body)[1])
  with self.assertRaises(ValueError):c.unpack({"message":"API changed"})
  with self.assertRaises(ValueError):c.unpack([])

 def test_bad_ids_dates_and_old_rows_rejected(self):
  self.assertIsNone(c.record(hit("0")))
  self.assertIsNone(c.record(hit("123",date="nonsense")))
  self.assertIsNone(c.record({"_source":{"company":"Example Bank"}}))
  old=c.record(hit("12345679",date="2026-01-01"))
  fresh=c.record(hit())
  fresh["complaint_what_happened"]="An accidentally supplied narrative"
  fresh["zip_code"]="12345"
  rows=c.retain([old,fresh,fresh],NOW)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["id"],"12345678")
  self.assertNotIn("complaint_what_happened",rows[0])
  self.assertNotIn("zip_code",rows[0])

 def test_request_uses_documented_100_result_search_not_export(self):
  response=Mock()
  response.content=b'{"ok":true}'
  response.json.return_value={"hits":{"hits":[hit()],"total":{"value":1,"relation":"eq"}}}
  session=Mock()
  session.get.return_value=response
  rows,total,start=c.collect(session,NOW)
  self.assertEqual(total,1)
  self.assertEqual(len(rows),1)
  self.assertEqual(start,"2026-08-01")
  kwargs=session.get.call_args.kwargs
  self.assertEqual(kwargs["params"]["size"],100)
  self.assertEqual(kwargs["params"]["sort"],"created_date_desc")
  self.assertEqual(kwargs["params"]["no_aggs"],"true")
  self.assertNotIn("format",kwargs["params"])
  self.assertIn("application/json",kwargs["headers"]["Accept"])

 def test_offline_preserves_existing_and_no_fake_success(self):
  with tempfile.TemporaryDirectory() as folder:
   dest=Path(folder)
   with patch.object(c,"OUT",dest/"data.json"),patch.object(c,"STATUS",dest/"status.json"),patch.object(c,"utcnow",lambda:NOW),patch.dict(os.environ,{"CFPB_OFFLINE":"1"}):
    c.save(c.OUT,{"complaints":[c.record(hit())]})
    c.run()
    status=json.loads(c.STATUS.read_text())
    rows=json.loads(c.OUT.read_text())["complaints"]
    self.assertEqual(status["status"],"offline_not_scanned")
    self.assertEqual(status["stored_records"],1)
    self.assertIsNone(status["latest_window_total"])
    self.assertEqual(len(rows),1)

 def test_external_response_failures_do_not_replace_existing_records(self):
  with tempfile.TemporaryDirectory() as folder:
   dest=Path(folder)
   with patch.object(c,"OUT",dest/"data.json"),patch.object(c,"STATUS",dest/"status.json"),patch.object(c,"utcnow",lambda:NOW),patch.object(c,"collect",side_effect=ValueError("Upstream HTML not JSON")),patch.dict(os.environ,{"CFPB_OFFLINE":"0"}):
    c.save(c.OUT,{"complaints":[c.record(hit())]})
    c.run()
    status=json.loads(c.STATUS.read_text())
    self.assertEqual(status["status"],"error")
    self.assertEqual(status["error_type"],"ValueError")
    self.assertEqual(status["stored_records"],1)
    self.assertIsNone(status["latest_window_total"])
if __name__=="__main__":unittest.main()
