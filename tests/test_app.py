import unittest
from importlib import resources

from mailwyrm.app import (
    _query_int,
    _query_mailbox,
    _query_workflow,
    build_workflow_preview_payload,
    create_app_server,
)
from mailwyrm.models import (
    AutomationPolicy,
    ClassificationRecord,
    DigestAuditEvent,
    MessageRecord,
)
from mailwyrm.store import MailwyrmState


def message(message_id: str, subject: str) -> MessageRecord:
    return MessageRecord(
        id=message_id,
        thread_id=f"thread-{message_id}",
        history_id="10",
        internal_date="1710000000000",
        label_ids=["INBOX"],
        snippet="Snippet",
        headers={"From": "Sender <sender@example.com>", "Subject": subject},
    )


def classification(message_id: str, *, suggested_actions=None) -> ClassificationRecord:
    return ClassificationRecord(
        message_id=message_id,
        category="machine",
        machine_type="notification",
        importance="low",
        automation_safety="high",
        confidence=0.94,
        reason="Automated sender or subject pattern.",
        suggested_actions=suggested_actions or ["digest", "archive"],
        classifier_version="rules-v0",
    )


class AppTest(unittest.TestCase):
    def test_app_static_assets_are_packaged_with_mailwyrm(self) -> None:
        static_root = resources.files("mailwyrm").joinpath("static")

        self.assertIn("<title>Mailwyrm</title>", static_root.joinpath("index.html").read_text())
        self.assertIn("Daily cockpit", static_root.joinpath("index.html").read_text())
        self.assertIn("human-lane", static_root.joinpath("index.html").read_text())
        self.assertIn("review-lane", static_root.joinpath("index.html").read_text())
        self.assertIn("workflows", static_root.joinpath("index.html").read_text())
        self.assertIn("/api/daily-cockpit", static_root.joinpath("app.js").read_text())
        self.assertIn("copy-command", static_root.joinpath("app.js").read_text())
        self.assertIn("workflow-status", static_root.joinpath("app.js").read_text())
        self.assertIn("/api/workflow-preview", static_root.joinpath("app.js").read_text())
        self.assertIn("preview-panel", static_root.joinpath("index.html").read_text())

    def test_query_int_accepts_zero_and_positive_values(self) -> None:
        self.assertEqual(_query_int({"limit": ["0"]}, "limit", 25), 0)
        self.assertEqual(_query_int({"limit": ["10"]}, "limit", 25), 10)
        self.assertEqual(_query_int({}, "limit", 25), 25)

    def test_query_int_rejects_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            _query_int({"limit": ["-1"]}, "limit", 25)

        with self.assertRaises(ValueError):
            _query_int({"limit": ["many"]}, "limit", 25)

    def test_query_mailbox_accepts_supported_mailboxes(self) -> None:
        self.assertEqual(_query_mailbox({}, "inbox"), "inbox")
        self.assertEqual(
            _query_mailbox({"mailbox": ["all-mail"]}, "inbox"),
            "all-mail",
        )
        self.assertEqual(_query_mailbox({"mailbox": ["trash"]}, "inbox"), "trash")

    def test_query_mailbox_rejects_unknown_mailboxes(self) -> None:
        with self.assertRaises(ValueError):
            _query_mailbox({"mailbox": ["spam"]}, "inbox")

        with self.assertRaises(ValueError):
            create_app_server(mailbox="spam")

    def test_query_workflow_accepts_preview_workflows(self) -> None:
        self.assertEqual(
            _query_workflow({"workflow": ["daily-preview"]}),
            "daily-preview",
        )
        self.assertEqual(_query_workflow({"workflow": ["labels"]}), "labels")
        self.assertEqual(_query_workflow({"workflow": ["archive"]}), "archive")
        self.assertEqual(_query_workflow({"workflow": ["trash"]}), "trash")

    def test_query_workflow_rejects_non_preview_workflows(self) -> None:
        with self.assertRaises(ValueError):
            _query_workflow({"workflow": ["sync"]})

    def test_build_workflow_preview_payload_renders_daily_preview(self) -> None:
        state = MailwyrmState(
            messages={"msg-1": message("msg-1", "Receipt")},
            classifications={"msg-1": classification("msg-1")},
        )

        payload = build_workflow_preview_payload(
            state,
            workflow="daily-preview",
            mailbox="inbox",
            limit=10,
        )

        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["title"], "Daily Workflow Preview")
        self.assertIn("No Gmail labels", payload["report"])
        self.assertIn("Mailbox scope: inbox", payload["report"])

    def test_build_workflow_preview_payload_renders_label_preview(self) -> None:
        state = MailwyrmState(
            messages={"msg-1": message("msg-1", "Receipt")},
            classifications={"msg-1": classification("msg-1")},
        )

        payload = build_workflow_preview_payload(
            state,
            workflow="labels",
            mailbox="inbox",
        )

        self.assertEqual(payload["title"], "Gmail Label Preview")
        self.assertIn("Mailwyrm/Machine", payload["report"])

    def test_build_workflow_preview_payload_renders_archive_preview(self) -> None:
        state = MailwyrmState(
            messages={"msg-1": message("msg-1", "Receipt")},
            classifications={"msg-1": classification("msg-1")},
        )

        payload = build_workflow_preview_payload(
            state,
            workflow="archive",
            mailbox="inbox",
        )

        self.assertEqual(payload["title"], "Mailbox Action Preview")
        self.assertIn("archive_after_digest", payload["report"])

    def test_build_workflow_preview_payload_renders_trash_preview(self) -> None:
        state = MailwyrmState(
            messages={"msg-1": message("msg-1", "Copilot")},
            classifications={
                "msg-1": classification(
                    "msg-1",
                    suggested_actions=["digest", "trash"],
                )
            },
            digest_audit_events=[
                DigestAuditEvent(
                    message_id="msg-1",
                    digest_title_date="2026-05-26",
                    reason="Low-risk notification.",
                    classifier_version="rules-v0",
                    created_at="2026-05-26T00:00:00+00:00",
                )
            ],
            automation_policy=AutomationPolicy(trash_after_digest_enabled=True),
        )

        payload = build_workflow_preview_payload(
            state,
            workflow="trash",
            mailbox="inbox",
        )

        self.assertEqual(payload["title"], "Trash Policy Preview")
        self.assertIn("Trash policy: enabled", payload["report"])
        self.assertIn("trash_after_digest", payload["report"])
