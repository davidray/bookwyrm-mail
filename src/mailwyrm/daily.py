from __future__ import annotations

from mailwyrm.actions import build_action_plans, render_action_preview
from mailwyrm.digest import render_digest
from mailwyrm.labels import build_digested_label_plans, render_digested_label_preview
from mailwyrm.store import MailwyrmState


def render_daily_preview(
    state: MailwyrmState,
    *,
    title_date: str,
    limit: int | None = None,
    mailbox: str = "inbox",
) -> str:
    digested_label_plans = build_digested_label_plans(state, limit=limit)
    action_plans = build_action_plans(state, limit=limit, mailbox=mailbox)

    sections = [
        f"# Mailwyrm Daily Preview - {title_date}",
        "",
        "This is a preview. No Gmail labels, archive state, or local digest audit state will be changed.",
        "",
        "## Machine Digest",
        "",
        render_digest(state, title_date=title_date),
        "",
        "## Gmail Digested Labels",
        "",
        "Candidates come from messages that already have local digest audit events.",
        "",
        render_digested_label_preview(digested_label_plans),
        "",
        "## Mailbox Actions",
        "",
        f"Mailbox scope: {mailbox}",
        "Archive apply remains gated to messages that have appeared in a digest.",
        "",
        render_action_preview(action_plans),
        "",
    ]
    return "\n".join(sections)
