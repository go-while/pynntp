# Council R1 — 8: fix/head-read-all

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `edbe1999829b0afd37df4ab65957875d83850046`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

HEAD consumes the registered reply to its dot before parsing, so an early
blank/bad header no longer leaves a live partially read reply. Parsing still
stops at the first blank line, and later response lines are intentionally
ignored. The raw bytes are decoded only after transport completion.

ARTICLE retains streaming into the body. If header parsing raises ValueError
(including strict-decoding errors), it drains the same raw reply iterator
before converting the error. A drain failure instead propagates the real
transport failure; _response's existing finally marks the session broken.
Successful drain permits reuse. The submitted regression cases cover both
successful drain and disconnect during it. No new issue in these paths found.

Verification: implementation/caller/error-lifecycle reading only; optional host
checks not run. No local execution, tree edits, commits, installs or GitHub
writes. G1 observed.

8 fix/head-read-all: 10, 0 findings (0H/0M/0L)
