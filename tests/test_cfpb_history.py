"""CFPB historical complaint coverage with explicit exact/sampled distinction."""
import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock,patch
from scripts import collect_cfpb_history as h

NOW=datetime(2026,10,30,12,0,tzinfo=timezone.utc)
def item(cid,date,issue="Unauthorized transactions",sub="Card stolen"):
 return {"_id":str(cid),"_source":{
  "complaint_id":cid,"date_received":date,
  "company":"Example Financial Institution","product":"Credit card",
  "issue":issue,"sub_issue":sub,
  "consumer_narrative":"private record not available",
  "zip_code":"10001",
 }}
class CFPBHistoryTests(unittest.TestCase):
 def test_available_history_reaches_december_2011(self):
  months=h.month_sequence(NOW)
  self.assertEqual(months[0],"2026-09")
  self.assertEqual(months[-1],"2011-12")
  self.assertEqual(len(months),178)
  self.assertEqual(h.boundaries("2011-12"),("2011-12-01","2012-01-01"))
  self.assertEqual(h.boundaries("2024-02"),("2024-02-01","2024-03-01"))
  self.assertEqual(h.month_sequence(datetime(2012,1,25,tzinfo=timezone.utc)),["2011-12"])

 def test_month_total_exact_but_issue_only_from_100_sample(self):
  response=Mock()
  response.content=b'{"ok":true}'
  response.json.return_value={"hits":{
    "hits":[item(1,"2011-12-18"),item(2,"2011-12-19"),item(3,"2012-01-01")],
    "total":{"value":3456,"relation":"eq"},
  }}
  session=Mock();session.get.return_value=response
  row=h.monthly_query("2011-12",session=session)
  self.assertIsNone(row["exact_published_complaint_total"])
  self.assertEqual(row["monthly_total_status"],"unverified_date_scope")
  self.assertEqual(row["api_hits_outside_requested_month"],1)
  # CFPB may return a non-month sample despite the requested date bounds.
  # Never label the associated numeric total as a verified month's count.
  response.json.return_value["hits"]["hits"]=[
    item(1,"2011-12-18"),item(2,"2011-12-19")]
  row=h.monthly_query("2011-12",session=session)
  self.assertEqual(row["exact_published_complaint_total"],3456)
  self.assertEqual(row["sample_size"],2)
  self.assertEqual(row["sample_issue_breakdown"][0]["sample_count"],2)
  self.assertEqual(row["monthly_total_status"],"exact_api_total")
  self.assertIn("NOT full issue/product counts",row["sample_basis"])
  self.assertNotIn("private record",json.dumps(row))
  kwargs=session.get.call_args.kwargs
  self.assertEqual(kwargs["params"]["date_received_max"],"2012-01-01")
  self.assertEqual(kwargs["params"]["size"],100)
  self.assertEqual(kwargs["params"]["no_aggs"],"true")
  response.json.return_value["hits"]["total"]["relation"]="gte"
  row=h.monthly_query("2011-12",session=session)
  self.assertIsNone(row["exact_published_complaint_total"])
  self.assertEqual(row["monthly_total_status"],"unknown_api_total")
  # A positive hit total with no reconstructable published examples must be
  # marked unverified, not asserted as an exact historical count.
  response.json.return_value["hits"]["total"]={"value":999,"relation":"eq"}
  response.json.return_value["hits"]["hits"]=[]
  row=h.monthly_query("2011-12",session=session)
  self.assertEqual(row["monthly_total_status"],"unverified_date_scope")
  self.assertIsNone(row["exact_published_complaint_total"])

 def test_rotating_month_cursor_and_failures_preserve_completed_months(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)
   calls=[]
   def fake_query(month,session=None):
    calls.append(month)
    if month=="2026-08":raise ValueError("upstream API error")
    return {"month":month,"date_received_min":month+"-01",
       "monthly_total_status":"exact_api_total",
       "exact_published_complaint_total":42,"sample_size":2,
       "sample_issue_breakdown":[],"sample_product_breakdown":[]}
   with patch.object(h,"OUT",path/"data.json"),patch.object(h,"STATUS",path/"health.json"),patch.object(h,"STATE",path/"state.json"),patch.object(h.c,"utcnow",lambda:NOW),patch.object(h,"monthly_query",side_effect=fake_query),patch.dict(os.environ,{"CFPB_HISTORY_BATCH":"3","CFPB_HISTORY_OFFLINE":"0"}):
    h.run()
    status=json.loads(h.STATUS.read_text())
    self.assertEqual(calls,["2026-09","2026-08","2026-07"])
    self.assertEqual(status["status"],"partial_error")
    self.assertEqual(status["months_with_results"],2)
    self.assertEqual(status["months_with_exact_totals"],2)
    self.assertEqual(json.loads(h.STATE.read_text())["next_cursor"],3)
    h.run()
    self.assertEqual(calls[3:],["2026-06","2026-05","2026-04"])
    self.assertEqual(len(json.loads(h.OUT.read_text())["months"]),5)

 def test_offline_cannot_claim_success_or_replace_real_totals(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)
   with patch.object(h,"OUT",path/"data.json"),patch.object(h,"STATUS",path/"health.json"),patch.object(h,"STATE",path/"state.json"),patch.object(h.c,"utcnow",lambda:NOW),patch.dict(os.environ,{"CFPB_HISTORY_OFFLINE":"1"}):
    h.c.save(h.OUT,{"months":[{"month":"2011-12","monthly_total_status":"exact_api_total","exact_published_complaint_total":123}]})
    h.run()
    data=json.loads(h.OUT.read_text())
    health=json.loads(h.STATUS.read_text())
    self.assertEqual(health["status"],"offline_not_scanned")
    self.assertEqual(data["months"][0]["month"],"2011-12")
    self.assertIsNone(data["months"][0]["exact_published_complaint_total"])
    self.assertEqual(data["months"][0]["monthly_total_status"],"unverified_date_scope")

if __name__=="__main__":unittest.main()
