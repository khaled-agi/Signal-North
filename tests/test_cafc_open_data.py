"""CAFC official Canada-only aggregation and small-cell privacy tests."""
import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
from scripts import collect_cafc_open_data as c

HEADER="Number ID,Date Received,Country,Province/State,Fraud and Cybercrime Thematic Categories,Solicitation Method,Number of Victims,Dollar Loss,Gender,Victim Age Range\n"
def file_text():
 rows=[]
 for i in range(6):
  rows.append(f'{i+1},2025-09-20,Canada,Ontario,Investment Fraud,Phone,1,"$1,500.00",Female,30-39')
 for i in range(3):
  rows.append(f'{i+10},2025-09-20,Canada,Alberta,Other Fraud,Email,1,"$300.00",Male,25-29')
 rows.append('99,2025-09-20,United States,California,Investment Fraud,Phone,1,"$2,000.00",Male,50-59')
 rows.append('100,broken,Canada,Ontario,Investment Fraud,Phone,1,"$20.00",Female,50-59')
 return HEADER+"\n".join(rows)+"\n"
class CAFCDataTests(unittest.TestCase):
 def test_valid_CAF_fields_and_reporting_lag(self):
  self.assertEqual(c.datepart("2025-09-30"),"2025-09-30")
  self.assertIsNone(c.datepart("garbage"))
  self.assertEqual(c.amount("$1,234.56"),1234.56)
  self.assertIsNone(c.amount(""))
  self.assertIsNone(c.amount("secret 25"))
  self.assertEqual(c.positive_int("1,200"),1200)
  self.assertEqual(c.EXPECTED_LAST_DATE,"2025-09-30")

 def test_does_not_publish_individual_identity_or_small_cells(self):
  rows,tally=c.aggregate(io.StringIO(file_text()))
  self.assertEqual(tally["rows_read"],11)
  self.assertEqual(tally["canada_rows"],9)
  self.assertEqual(tally["outside_canada_rows"],1)
  self.assertEqual(tally["invalid_date"],1)
  ontario=[x for x in rows if x["dimension"]=="province" and x["label"]=="Ontario"]
  self.assertEqual(len(ontario),1)
  self.assertEqual(ontario[0]["report_rows"],6)
  self.assertEqual(ontario[0]["reported_dollar_loss_sum"],9000.0)
  self.assertEqual(ontario[0]["reported_victims_sum"],6)
  self.assertFalse(any(x["dimension"]=="province" and x["label"]=="Alberta" for x in rows))
  self.assertFalse(any(x["dimension"]=="province" and x["label"]=="California" for x in rows))
  self.assertFalse(any("gender" in x or "age" in x or "Number ID" in x for x in rows))
  self.assertNotIn("Female",json.dumps(rows))

 def test_missing_loss_does_not_become_zero(self):
  text=HEADER+"\n".join(
    f'{i+1},2024-08-12,Canada,Quebec,Phishing,Text,1,' for i in range(6))+"\n"
  rows,_=c.aggregate(io.StringIO(text))
  year=[r for r in rows if r["dimension"]=="year"]
  self.assertEqual(year[0]["report_rows"],6)
  self.assertIsNone(year[0]["reported_dollar_loss_sum"])
  self.assertEqual(year[0]["rows_without_loss"],6)

 def test_fails_closed_on_schema_change(self):
  with self.assertRaises(ValueError):c.aggregate(io.StringIO("First,Second\none,two\n"))

 def test_offline_and_download_errors_do_not_create_data(self):
  now=datetime(2026,10,30,20,tzinfo=timezone.utc)
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder)
   with patch.object(c,"OUT",d/"data.json"),patch.object(c,"STATUS",d/"status.json"),patch.object(c,"now",lambda:now),patch.dict(os.environ,{"CAFC_OFFLINE":"1"}):
    c.run()
    status=json.loads(c.STATUS.read_text())
    self.assertEqual(status["status"],"offline_not_scanned")
    self.assertFalse(c.OUT.exists())
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder)
   with patch.object(c,"OUT",d/"data.json"),patch.object(c,"STATUS",d/"status.json"),patch.object(c,"now",lambda:now),patch.object(c,"stream_csv",side_effect=ValueError("feed unavailable")),patch.dict(os.environ,{"CAFC_OFFLINE":"0"}):
    c.run()
    self.assertEqual(json.loads(c.STATUS.read_text())["status"],"error")
    self.assertFalse(c.OUT.exists())

if __name__=="__main__":unittest.main()
