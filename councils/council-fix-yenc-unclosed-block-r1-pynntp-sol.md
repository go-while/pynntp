# Council R1 — 1: fix/yenc-unclosed-block

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `2cf7f35ad83a4bc7ed44ce7e6e9444e38024081f`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Read the exact implementation and regression diff. The new check runs after
pending bytes of the previous block are decoded, but before resetting its
decoder/size/open flag. Therefore a second `=ybegin ` cannot erase the fact that
the first block lacked its trailer. The saved error survives subsequent valid
trailers and both blocks' bytes remain in NNTPYEncError.data. A normally closed
block followed by another block is unaffected. The added regression also checks
the following DATE, consistent with reading the whole response before raising.

Verification: code reading only; optional test-host execution was not used.
No code run locally, tree edits, commits, installs or GitHub writes. G1 observed.

1 fix/yenc-unclosed-block: 10, 0 findings (0H/0M/0L)
