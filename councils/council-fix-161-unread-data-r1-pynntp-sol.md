# Council R1 — 10: fix/161-unread-data

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `976d46ee0f8687857d9334f273c4d1ae6594c229`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Reviewed _check_nothing_unread(), its _command and _transfer call sites, and
the compression/response helpers. Both checks run under _sync, so a refused
send reliably marks the connection broken. Commands already blocked by an
active reply or closed session still take the earlier synchronization guards.
POST/IHAVE now also check between the ready reply and transmitting the article.

Pending output from a saturated transport decompressor is examined as well as
_buffer. A compression flush producing no application bytes does not itself
cause rejection. Existing COMPRESS startup processing consumes pending raw
compression bytes before this guard is consulted.

The boundary is deliberately already-received application data: the patch does
not pretend to detect unsolicited bytes still unread on the socket or arriving
later. That is stated in the test comments and is not counted as a missing
hardening feature. Tests now use reply-end recv boundaries, with explicit
Packets for coalesced/malformed replies, gzip and COMPRESS pending-data cases.
I inspected those helper semantics; they change chunking, not the byte stream.

Verification: high-attention source review of read/sync/COMPRESS paths only;
optional VM tests not run. No local project execution, tree edits, commits,
installs, queue claims or GitHub writes. G1 observed.

10 fix/161-unread-data: 10, 0 findings (0H/0M/0L)
