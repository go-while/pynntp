# Council R1 — 3: fix/reconnect-failure-broken

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `0ae1bd3c21a0eb28495e142a20571e43abc660d5`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Traced BaseNNTPClient._connect(), reconnect(), close() and the reader-level
connection wrapper. reconnect() marks the old connection closed before calling
_connect(). Delaying `_broken=False` until create_connection succeeds retains
that state on a refused/timed-out connection, while allowing a later retry.
TLS and greeting failures still run the existing close path. Failure during
initial construction does not return a usable client, so the delayed first
assignment does not expose an uninitialized client in normal use.

The added flaky-connection test covers refusal, refusal of subsequent commands,
and a successful second reconnect. No unrelated synchronization policy changes.

Verification: exact diff and source reading; optional host checks not run.
No tree edits, local project execution, commits, installs or GitHub writes.
G1 observed.

3 fix/reconnect-failure-broken: 10, 0 findings (0H/0M/0L)
