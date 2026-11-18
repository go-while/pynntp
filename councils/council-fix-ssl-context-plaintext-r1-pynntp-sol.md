# Council R1 — 9: fix/ssl-context-plaintext

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `c63cc598818a07295f2a95e63c7af259a97260de`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Constructor validation normalizes SSLMode before opening a socket, rejects
invalid modes, and refuses a supplied TLS context or STARTTLS mode on a
plaintext client. This closes the silent-ignore route without silently choosing
a different protocol/port for the caller.

from_url() separately rejects TLS context with the plaintext nntp scheme.
Its error text names allowed schemes, not the supplied URL or credentials.
TLS schemes still pass the exact context through, preserving caller-provided
certificate policy; ordinary plaintext clients without TLS settings remain
supported. Reconnect uses the validated stored mode. Read the constructor,
URL construction and changed integration call sites; no regression identified.

Verification: high-attention TLS/credential control-flow review, not an actual
TLS handshake or executed tests. Optional host execution not used. No local
project execution, tree edits, commits, installs or GitHub writes. G1 observed.

9 fix/ssl-context-plaintext: 10, 0 findings (0H/0M/0L)
