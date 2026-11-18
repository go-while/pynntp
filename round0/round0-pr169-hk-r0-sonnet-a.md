# Round 0 review: PR #169 (fix/156-post-msgid, eaa79ed) by hk-r0-sonnet-a

Method: read the net diff `upstream/main...origin/fix/156-post-msgid`, `post()`/`_transfer()`/`_MESSAGE_ID_RE` at the head, the PR body and issue #156. No host run; nothing here claims tests passed.

Score: 9 / 10. Findings: none (one design trade-off in the notes).

## What the change does
`post()` no longer searches the 240 text. It splits on whitespace, drops a leading `Article received` (case-insensitive), and returns the next token only if `_MESSAGE_ID_RE.fullmatch` accepts it (RFC 3977 syntax, 1-248 chars). Anything else returns True. Docstring updated.

## Checks (by reading)
- Regex `<[!-=?-~]{1,248}>` is shared with other code (nntp.py:1393, 1849) and unchanged; fullmatch on a whitespace-free token is correct.
- `message.split()` handles runs of spaces, tabs, an empty message ("240" -> parts empty -> True), and non-ASCII whitespace harmlessly.
- `casefold` on "article"/"received" cannot be fooled by special folds (no ss/long-s style letters in them).
- `<bad<id>` accepted (RFC allows an inner "<"); `<>`, `<bad id>`, 249-char ids and `<id>suffix`/`prefix<id>`/`(<id>)` give True. Tests cover each.
- The reply is read in full before parsing (`_transfer`), so the connection stays in sync on any reply text; the new test adds `client.date()` after each reply.
- Tests would fail on base for the free-text and boundary rows (base used `search`). Rows that return the id for INN/Diablo/OUS forms pass on both.
- Docstring matches the code. README line 108 ("returns the new article's message-id if the server reports it") stays true.

## Notes (non-findings)
- Trade-off: a server that puts the id somewhere else (e.g. `240 Article posted <id>`, `240 OK <id>`, `240 <id>.`) used to give the id and now gives True. The return type and docs already say the id is optional and "not standard", the only observable harm is that the caller must look the id up some other way, and I know of no such server from the repo's own notes (INN, Diablo, OUS, NewsCache, go-pugleaf are covered by the tests). Judged a deliberate, documented narrowing, not a bug; the lead may want to say so in the PR text.
- A server that sends `240 <abuse@example.net> ...` as its first token would still be taken as the id; there is no way to tell it from a real one, and the server is the user's chosen one.
- Two commits (d75cdcd, eaa79ed) for one concern: fine.

## Not checked
No host run. Did not test against a real INN/Diablo reply.
