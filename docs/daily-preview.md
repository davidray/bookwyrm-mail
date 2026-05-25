# Daily Preview

`mailwyrm daily preview` renders the first single-report daily machine-mail workflow.

It is intentionally preview-only. It does not mark messages as digested, apply Gmail labels, archive messages, trash messages, or write local audit events.

The report combines:

- The local machine-mail digest.
- Gmail `Mailwyrm/Digested` label candidates from existing local digest audit events.
- Mailbox action candidates for the selected mailbox scope.

The default mailbox scope for mailbox actions is `inbox`, matching Mailwyrm's attention-first default. Use `--mailbox all-mail` when reviewing long-term cleanup candidates outside the inbox.

Example:

```sh
uv run mailwyrm daily preview --limit 25
uv run mailwyrm daily preview --mailbox all-mail --limit 100
```

Archive apply remains gated to messages that have already appeared in a digest. The daily preview may show archive candidates, but the Gmail-mutating archive command will still skip candidates that lack a local digest audit event.
