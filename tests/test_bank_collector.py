import unittest
from scripts.collect_bank_complaints import parse_national_bank

class BankCollectorTest(unittest.TestCase):
 def test_nbc(self):
  x=parse_national_bank("<html><body><h2>Annual Data</h2><p>2025</p><table><tr><td>Number of complaints reviewed by the Client Complaint Appeal Office</td><td>2,704</td></tr></table><p>Main reason for complaint Fraud 15%</p></body></html>")
  self.assertEqual(x["metric_value"],2704)
  self.assertEqual(x["fraud_nature_pct"],15.0)
 def test_no_data_rejected(self):
  with self.assertRaises(ValueError):parse_national_bank("<html><p>Access denied</p></html>")
