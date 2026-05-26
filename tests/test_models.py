import unittest

from mailwyrm.models import MessageRecord


class MessageRecordTest(unittest.TestCase):
    def test_message_record_from_gmail_metadata(self) -> None:
        message = {
            "id": "msg-1",
            "threadId": "thread-1",
            "historyId": "42",
            "internalDate": "1710000000000",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "hello there",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Ada <ada@example.com>"},
                    {"name": "Subject", "value": "Hello"},
                ]
            },
        }

        record = MessageRecord.from_gmail_message(message)

        self.assertEqual(record.id, "msg-1")
        self.assertEqual(record.thread_id, "thread-1")
        self.assertEqual(record.history_id, "42")
        self.assertEqual(record.label_ids, ["INBOX", "UNREAD"])
        self.assertEqual(record.headers["From"], "Ada <ada@example.com>")
        self.assertEqual(record.headers["Subject"], "Hello")

    def test_message_record_decodes_html_entities_in_gmail_snippet(self) -> None:
        message = {
            "id": "msg-1",
            "threadId": "thread-1",
            "snippet": "Elder Christiansen&#39;s account &amp; correspondence",
            "payload": {"headers": []},
        }

        record = MessageRecord.from_gmail_message(message)

        self.assertEqual(
            record.snippet,
            "Elder Christiansen's account & correspondence",
        )

    def test_message_record_decodes_html_entities_from_local_state(self) -> None:
        record = MessageRecord.from_dict(
            {
                "id": "msg-1",
                "thread_id": "thread-1",
                "snippet": "Please check Elder Christiansen&#39;s account.",
            }
        )

        self.assertEqual(
            record.snippet,
            "Please check Elder Christiansen's account.",
        )


if __name__ == "__main__":
    unittest.main()
