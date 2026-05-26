# Gmail History Reconciliation

Mailwyrm can reconcile Gmail label and deletion changes from the stored Gmail history cursor.

This keeps Gmail as the source of truth when mailbox state changes outside Mailwyrm, such as archiving a message in Gmail, moving it to Trash, marking it unread, or applying labels.

## Command

```sh
uv run mailwyrm sync-history --client-secret /path/to/client_secret.json
uv run mailwyrm sync-history --client-secret /path/to/client_secret.json --max-pages 25
```

Run `mailwyrm sync` first so local state has a Gmail `history_id` cursor.

## What It Does

`sync-history` reads Gmail history events after the stored cursor and applies them to messages already in the local Mailwyrm index.

Current behavior:

- Applies `labelsAdded` events to local `label_ids`.
- Applies `labelsRemoved` events to local `label_ids`.
- Removes locally indexed messages when Gmail reports `messagesDeleted`.
- Advances the stored Gmail history cursor when Gmail returns a newer `historyId`.
- Reports unknown message IDs instead of fetching them.

This command is read-only from Gmail's perspective. It does not apply labels, archive, trash, mark read or unread, or otherwise mutate Gmail.

## Current Limitations

This first reconciliation slice does not fetch new messages that appear in history, and it does not yet recover from an expired or too-old Gmail history cursor. If Gmail reports a missed history window, the repair path should be a broader scoped sync against Gmail.

Future work should add:

- Fetching newly seen messages from history when appropriate.
- Explicit recovery messaging for expired history cursors.
- App-surface status for last reconciliation and missed-history recovery.
