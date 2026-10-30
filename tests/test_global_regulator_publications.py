"""Source-domain and evidence integrity regression for international regulator discovery."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from scripts.collect_global_regulator_publications import (
    REGULATORS, parse_results, original_official_link, query_url_params, ACTIONS,
)
from scripts.collect_global import scan_mas

class EnforcementDiscoveryTests(unittest.TestCase):
    def test_original_regulator_domain_only(self):
        self.assertIsNotNone(original_official_link(
            "https://www.mas.gov.sg/regulation/enforcement/enforcement-actions","mas.gov.sg"))
        self.assertIsNone(original_official_link(
            "https://mas.gov.sg.attacker.invalid/enforcement/fine","mas.gov.sg"))
        self.assertIsNone(original_official_link(
            "http://www.mas.gov.sg/regulation/enforcement","mas.gov.sg"))
        self.assertIsNone(original_official_link(
            "https://news.google.com/rss/articles/abc","mas.gov.sg"))
        self.assertIsNone(original_official_link(
            "https://www.gov.br/health/announcement","gov.br"))
        self.assertIsNotNone(original_official_link(
            "https://www.gov.br/cvm/pt-br/noticias/2026","gov.br"))

    def test_regulators_not_confused_with_country_coverage(self):
        self.assertGreaterEqual(len(REGULATORS),25)
        self.assertGreaterEqual(len({x[0] for x in REGULATORS}),15)
        self.assertLess(len({x[0] for x in REGULATORS}),250)
        self.assertTrue(all(query_url_params(a)["query"].startswith("domain:") for a in REGULATORS))

    def test_gdelt_first_observed_is_not_publication_date(self):
        agency=("SG","Singapore","MAS","mas.gov.sg")
        now=datetime.now(timezone.utc)
        d=(now-timedelta(days=1)).strftime("%Y%m%d%H%M%S")
        payload={"articles":[
            {"title":"MAS imposes civil penalty on financial company","url":"https://mas.gov.sg/regulation/enforcement/2026/penalty","seendate":d},
            {"title":"MAS fines bank but link is third party","url":"https://example.com/mas/fine","seendate":d},
            {"title":"MAS enforcement policy guidance","url":"https://mas.gov.sg/regulation/enforcement/policy","seendate":d},
        ]}
        rows=parse_results(payload,agency,now)
        self.assertEqual(len(rows),1)
        x=rows[0]
        self.assertIsNone(x["published_at"])
        self.assertEqual(x["date_basis"],"gdelt_first_seen_not_official_publication_date")
        self.assertEqual(x["evidence_tier"],"official_site_publication_lead")
        self.assertIsNone(x["penalty_amount"])
        self.assertEqual(x["review_status"],"legal_status_and_action_type_not_independently_checked")
        self.assertNotIn("final",x["evidence_tier"])

    def test_mas_primary_index_parser_rejects_external_links(self):
        markup="""<html><body><table>
          <tr><td>29 October 2026</td><td>ABC Payments Pte Ltd</td>
              <td>Prohibition Order</td>
              <td><a href="/regulation/enforcement/abc">MAS issues prohibition order</a></td></tr>
          <tr><td>25 October 2026</td><td>XYZ Company</td>
              <td>Fine</td><td><a href="https://fake-mas.example/fine">Fined</a></td></tr>
        </table></body></html>"""
        response=Mock(text=markup);response.raise_for_status.return_value=None
        session=Mock();session.get.return_value=response
        rows=scan_mas(session)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["regulator"],"MAS")
        self.assertEqual(rows[0]["published_at"],"2026-10-29")
        self.assertEqual(rows[0]["evidence_tier"],"official_enforcement_index")
        self.assertEqual(rows[0]["penalty_amount"],None)

if __name__=="__main__":unittest.main()
