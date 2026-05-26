from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from mailwyrm.models import MessageRecord
from mailwyrm.store import MailwyrmState


@dataclass(frozen=True)
class SyncStats:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    label_changes: int = 0


@dataclass(frozen=True)
class HistoryReconcileStats:
    history_records: int = 0
    label_changes: int = 0
    messages_deleted: int = 0
    unknown_messages: int = 0
    cursor_advanced: bool = False
    unknown_message_ids: frozenset[str] = field(
        default_factory=frozenset,
        compare=False,
        repr=False,
    )


def refresh_message_from_gmail(
    state: MailwyrmState,
    record: MessageRecord,
    stats: SyncStats,
) -> SyncStats:
    previous = state.messages.get(record.id)
    state.messages[record.id] = record

    if previous is None:
        return SyncStats(
            fetched=stats.fetched + 1,
            new=stats.new + 1,
            updated=stats.updated,
            unchanged=stats.unchanged,
            label_changes=stats.label_changes,
        )

    changed = message_metadata_changed(previous, record)
    label_changed = set(previous.label_ids) != set(record.label_ids)
    return SyncStats(
        fetched=stats.fetched + 1,
        new=stats.new,
        updated=stats.updated + int(changed),
        unchanged=stats.unchanged + int(not changed),
        label_changes=stats.label_changes + int(label_changed),
    )


def render_sync_summary(stats: SyncStats, mailbox: str, account_email: str | None) -> str:
    return (
        f"Synced {stats.fetched} {mailbox} message(s) for "
        f"{account_email or 'unknown account'}. "
        f"New: {stats.new}; updated: {stats.updated}; "
        f"unchanged: {stats.unchanged}; "
        f"label changes: {stats.label_changes}."
    )


def reconcile_history(
    state: MailwyrmState,
    history_response: dict[str, Any],
) -> HistoryReconcileStats:
    stats = HistoryReconcileStats()
    seen_unknown_messages: set[str] = set()

    for history_record in history_response.get("history", []):
        stats = replace(stats, history_records=stats.history_records + 1)
        for label_event in history_record.get("labelsAdded", []):
            message_id = _history_message_id(label_event)
            if _record_unknown_message(state, message_id, seen_unknown_messages):
                continue
            label_changes = _add_labels(
                state,
                message_id,
                label_event.get("labelIds", []),
            )
            if label_changes:
                stats = replace(
                    stats,
                    label_changes=stats.label_changes + label_changes,
                )

        for label_event in history_record.get("labelsRemoved", []):
            message_id = _history_message_id(label_event)
            if _record_unknown_message(state, message_id, seen_unknown_messages):
                continue
            label_changes = _remove_labels(
                state,
                message_id,
                label_event.get("labelIds", []),
            )
            if label_changes:
                stats = replace(
                    stats,
                    label_changes=stats.label_changes + label_changes,
                )

        for deleted_event in history_record.get("messagesDeleted", []):
            message_id = _history_message_id(deleted_event)
            if not message_id:
                continue
            if message_id not in state.messages:
                seen_unknown_messages.add(message_id)
            if _remove_local_message(state, message_id):
                stats = replace(stats, messages_deleted=stats.messages_deleted + 1)

    stats = replace(
        stats,
        unknown_messages=len(seen_unknown_messages),
        unknown_message_ids=frozenset(seen_unknown_messages),
    )
    next_history_id = history_response.get("historyId")
    if next_history_id is not None and str(next_history_id) != str(state.history_id):
        state.history_id = str(next_history_id)
        stats = replace(stats, cursor_advanced=True)
    return stats


def merge_history_stats(
    left: HistoryReconcileStats,
    right: HistoryReconcileStats,
) -> HistoryReconcileStats:
    unknown_message_ids = left.unknown_message_ids | right.unknown_message_ids
    return HistoryReconcileStats(
        history_records=left.history_records + right.history_records,
        label_changes=left.label_changes + right.label_changes,
        messages_deleted=left.messages_deleted + right.messages_deleted,
        unknown_messages=len(unknown_message_ids),
        cursor_advanced=left.cursor_advanced or right.cursor_advanced,
        unknown_message_ids=unknown_message_ids,
    )


def render_history_reconcile_summary(
    stats: HistoryReconcileStats,
    account_email: str | None,
) -> str:
    cursor = "advanced" if stats.cursor_advanced else "unchanged"
    return (
        f"Reconciled {stats.history_records} Gmail history record(s) for "
        f"{account_email or 'unknown account'}. "
        f"Label changes: {stats.label_changes}; "
        f"deleted messages: {stats.messages_deleted}; "
        f"unknown messages: {stats.unknown_messages}; "
        f"cursor: {cursor}."
    )


def _history_message_id(event: dict[str, Any]) -> str:
    message = event.get("message") or {}
    message_id = message.get("id")
    return "" if message_id is None else str(message_id)


def _record_unknown_message(
    state: MailwyrmState,
    message_id: str,
    seen_unknown_messages: set[str],
) -> bool:
    if not message_id or message_id not in state.messages:
        if message_id:
            seen_unknown_messages.add(message_id)
        return True
    return False


def _add_labels(
    state: MailwyrmState,
    message_id: str,
    label_ids: list[str],
) -> int:
    message = state.messages[message_id]
    existing = set(message.label_ids)
    updated = existing | {str(label_id) for label_id in label_ids}
    if updated == existing:
        return 0
    state.messages[message_id] = replace(message, label_ids=sorted(updated))
    return len(updated - existing)


def _remove_labels(
    state: MailwyrmState,
    message_id: str,
    label_ids: list[str],
) -> int:
    message = state.messages[message_id]
    existing = set(message.label_ids)
    updated = existing - {str(label_id) for label_id in label_ids}
    if updated == existing:
        return 0
    state.messages[message_id] = replace(message, label_ids=sorted(updated))
    return len(existing - updated)


def _remove_local_message(state: MailwyrmState, message_id: str) -> bool:
    removed = False
    for records in (state.messages, state.classifications, state.corrections):
        if records.pop(message_id, None) is not None:
            removed = True
    return removed


def message_metadata_changed(previous: MessageRecord, record: MessageRecord) -> bool:
    return (
        previous.id != record.id
        or previous.thread_id != record.thread_id
        or previous.history_id != record.history_id
        or previous.internal_date != record.internal_date
        or set(previous.label_ids) != set(record.label_ids)
        or previous.snippet != record.snippet
        or previous.headers != record.headers
        or previous.body_text != record.body_text
    )
