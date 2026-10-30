"""No live API calls: validate safe social-signal extraction and retention rules."""
import unittest
from datetime import datetime, timedelta, timezone
from scripts.collect_community import classify, make_signal, MAX_DAYS

NOW = datetime(2026, 10, 30, 20, tzinfo=timezone.utc)

class CommunitySignalTests(unittest.TestCase):
    def test_bank_is_a_mention_not_a_liability_claim(self):
        x = make_signal("reddit", "r/Wealthsimple",
                        "https://www.reddit.com/r/Wealthsimple/comments/abc123/",
                        "Fake Wealthsimple support phished my OTP",
                        NOW, NOW)
        self.assertEqual(x["institutions_mentioned"], ["Wealthsimple"])
        self.assertEqual(x["topic"], "Bank impersonation")
        self.assertEqual(x["evidence_status"], "unverified_social_signal")
        self.assertNotIn("author", x)
        self.assertNotIn("body", x)
        self.assertNotIn("Fake Wealthsimple", str(x))

    def test_no_nonfraud_posts(self):
        self.assertIsNone(classify("Should I open a new checking account?"))

    def test_old_social_posts_expire(self):
        self.assertIsNone(make_signal("reddit", "r/Scams",
            "https://www.reddit.com/r/Scams/comments/abc123/",
            "Bank phishing scam", NOW - timedelta(days=MAX_DAYS + 1), NOW))

    def test_no_arbitrary_links(self):
        self.assertIsNone(make_signal("telegram", "@channel",
            "https://bad.example/steal", "Fake bank impersonation scam", NOW, NOW))
        self.assertIsNone(make_signal("reddit", "r/Scams",
            "javascript:alert(1)", "Fake bank impersonation scam", NOW, NOW))

    def test_redaction_uses_only_labels(self):
        x = make_signal("telegram", "@authorizedchannel",
            "https://t.me/authorizedchannel/53",
            "Phishing campaign from john@example.com call +1 416 555 9999, CIBC",
            NOW, NOW)
        self.assertIsNotNone(x)
        self.assertNotIn("john@example.com", str(x))
        self.assertNotIn("416", str(x))
        self.assertEqual(x["topic"], "Phishing / smishing")

    def test_no_ambiguous_geography(self):
        x = classify("Canada and USA phishing scams involving CIBC")
        self.assertIsNone(x["country_hint"])

if __name__ == "__main__":
    unittest.main()
