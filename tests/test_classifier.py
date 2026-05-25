import unittest

from mailwyrm.classifier import classify_message
from mailwyrm.models import MessageRecord


def message(
    *,
    sender: str,
    subject: str,
    snippet: str = "",
    message_id: str = "msg-1",
) -> MessageRecord:
    return MessageRecord(
        id=message_id,
        thread_id="thread-1",
        history_id="10",
        internal_date="1710000000000",
        label_ids=["INBOX"],
        snippet=snippet,
        headers={"From": sender, "Subject": subject},
    )


class ClassifierTest(unittest.TestCase):
    def test_classifies_machine_newsletter(self) -> None:
        classification = classify_message(
            message(sender="Newsletter <newsletter@example.com>", subject="Weekly newsletter")
        )

        self.assertEqual(classification.category, "machine")
        self.assertEqual(classification.machine_type, "newsletter")
        self.assertIn("digest", classification.suggested_actions)

    def test_protects_high_risk_machine_mail(self) -> None:
        classification = classify_message(
            message(
                sender="Security <no-reply@example.com>",
                subject="Security alert for your account",
            )
        )

        self.assertEqual(classification.category, "needs_review")
        self.assertEqual(classification.importance, "high")
        self.assertEqual(classification.automation_safety, "low")
        self.assertIn("protect", classification.suggested_actions)

    def test_plain_word_risk_terms_do_not_match_inside_other_words(self) -> None:
        classification = classify_message(
            message(
                sender="Updates <updates@example.com>",
                subject="Contact preferences changed",
                snippet="Your contact preferences were updated.",
            )
        )

        self.assertNotEqual(classification.importance, "high")
        self.assertNotIn("protect", classification.suggested_actions)

    def test_classifies_reply_as_human(self) -> None:
        classification = classify_message(
            message(sender="Ada <ada@example.com>", subject="Re: dinner tomorrow")
        )

        self.assertEqual(classification.category, "human")
        self.assertIsNone(classification.machine_type)


if __name__ == "__main__":
    unittest.main()
