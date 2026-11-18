# Council R1 — 11: fix/163-header-unfold, follow-up only

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Reviewed only `c6b040d3001e1ee2cef05f9b19ef88f71a88be0d` ..
`1c083aa174365651420f48fd74ae4e0f13016df6`, the specified follow-up to PR172.
The original whitespace-preservation patch is the base, not an extra finding.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

parse_headers() retains the same physical-line ending removal, blank-line stop,
continuation check, field-name handling, final outer trim and last-value-wins
mapping construction. The only semantic-neutral representation change is a
list of value pieces joined once instead of repeatedly concatenating the
accumulated string. This preserves fold whitespace while removing repeated
prefix copying for many continuations.

The added many-line test asserts both values, including a following header.
No local timing or replica experiment was performed, and no runtime performance
number is claimed in this review.

Verification: exact follow-up diff and code reading only; optional host checks
not run. No tree edits, local project execution, commits, installs or GitHub
writes. G1 observed.

11 fix/163-header-unfold: 10, 0 findings (0H/0M/0L)
