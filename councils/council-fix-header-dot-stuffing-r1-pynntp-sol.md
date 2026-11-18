# Council R1 — 5: fix/header-dot-stuffing

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `77e70a66a795a442e52f73a7923dcf4246f0424d`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Read _item_lines(), _prepare_article(), POST/IHAVE and serialization validation.
Headers and body now share line-level dot stuffing, preserving legal folded
continuations whose first byte is whitespace. The final protocol dot is still
written separately and never stuffed. Empty header/body handling preserves
the header/body separator.

For body iterables, splitting each item at LF before validating/stuffing
prevents a later interior dot line from bypassing stuffing. CRLF is normalized,
bare CR and NUL are rejected before the POST/IHAVE exchange, and an empty item
retains its previous empty-line meaning. The documented per-item line-boundary
contract is preserved for items without LF. The temporary-file preflight and
cleanup remain intact.

Verification: exact source/diff and wire-expectation tests read, not executed.
Optional host checks not run. No local execution, tree edits, commits, installs
or GitHub writes. G1 observed.

5 fix/header-dot-stuffing: 10, 0 findings (0H/0M/0L)
