import csv
import io
import unittest
from scripts.collect_uk_sanctions import parse_csv

class UKSanctionsPrimarySourceTests(unittest.TestCase):
 def test_uk_fcdos_csv_first_date_header_and_primary_names(self):
  header=["Unique ID","Name 6","Individual, Entity, Ship","Regime Name","Name type","Sanctions Imposed","Date Designated"]
  rows=[
   ["2026-10-30 official FCDO report"],
   header,
   ["UKS10001","DEMO LIMITED","Entity","Russia","Primary Name","Asset Freeze","02/02/2024"],
   ["UKS10001","DEMO LTD","Entity","Russia","Alias","Asset Freeze","02/02/2024"],
   ["UKS10002","TEST INDIVIDUAL","Individual","Russia","Primary Name","Travel Ban","03/03/2024"],
   ["UKS10003","TEST TRUST","Entity","Iran","Primary Name","Asset Freeze","04/04/2024"],
   ["UKS10004","TEST SHIP","Ship","Russia","Primary Name","Transport Ban","04/04/2024"],
  ]
  stream=io.StringIO();writer=csv.writer(stream);writer.writerows(rows)
  found,total=parse_csv(stream.getvalue().encode(),minimum=2)
  self.assertEqual(total,5)
  self.assertEqual(len(found),2)
  self.assertEqual(found[0]["name"],"DEMO LIMITED")
  self.assertEqual(found[0]["uk_unique_id"],"UKS10001")
  self.assertEqual(found[1]["regime"],"Iran")
 def test_bad_csv_schema_rejected(self):
  with self.assertRaises(ValueError):parse_csv(b"Access denied",minimum=1)

if __name__=="__main__":unittest.main()
