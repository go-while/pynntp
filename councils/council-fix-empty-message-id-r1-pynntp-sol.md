# Council R1 — 2: fix/empty-message-id

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `ca94d6ef5f03f2357d3e87d6672966ef3ff47ec5`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings under the updated Findings rule v2. | — | — |

The guards prevent empty/blank article arguments from silently selecting the
current article. None still selects the current article intentionally; scalar
bools now reject. STAT/ARTICLE/HEAD/BODY and HDR-family guards run before their
commands. Reviewed the changed call sites and submitted tests.

## Notes — not findings

- **Pre-existing / known in open PR176:** `_xover()` fetches overview format
  before argument validation (`nntp.py:1682–1689`). The new empty-input guard
  can therefore follow a format request on a cold cache. The separate #165/
  PR176 ordering fix covers this; the caller still fails loudly rather than
  silently operating on the wrong article. Not counted again as a row2 bug.
- The new docstring's blanket “Nothing is sent” requires that ordering
  prerequisite for cold-cache overview calls. This is an integration/doc
  qualification, not a rule-v2 data-loss finding.

Verification: source-verified call order; not a runtime reproduction. Optional
host execution was not used. No tree edits, local execution, commits, installs
or GitHub writes. G1 observed.

2 fix/empty-message-id: 10, 0 findings (0H/0M/0L)
