# Council R2b — 2: fix/empty-message-id

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `ca94d6ef5f03f2357d3e87d6672966ef3ff47ec5`.
Scope: the whole PR, helpers, callers, docstrings and submitted tests.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

- `_msgid_article()` distinguishes intentional None/current-article selection
  from empty/whitespace strings and scalar bools. Invalid arguments raise
  rather than silently selecting another article.
- STAT, ARTICLE, HEAD and BODY call that helper before sending their command.
  The shared utility rejects empty/blank range strings in HDR/XHDR/XZHDR/XPAT
  and overview methods, preserving nonempty strings and normal numeric ranges.
- Tests inspect no-send behavior and retain explicit None selection. The
  behavior changes are restricted to rejected inputs, not valid article IDs.

## Notes — not findings

- **Pre-existing, known/planned:** `_xover()` reads overview metadata before
  argument validation (`nntp.py:1682–1689`). Its blanket “Nothing is sent”
  docstring consequently needs the ordering change already in open PR176
  for a cold format cache. The overview test here deliberately warms it.
  This produces a loud failure, not silent wrong-article selection, and the
  existing ordering item is not counted again or used to reopen this PR's scope.
- Other known numeric/range validation items in #166 are not new findings here.

## Verification and limits

Source review only; no tests, real-server interaction or merged-PR validation
run. Known issues/PRs were checked read-only. No claim that my tests passed;
the lead's stated test results remain its evidence. No tree edits, commits,
installs, host jobs or GitHub writes. G1 observed.

2 fix/empty-message-id: 10, 0 findings (0H/0M/0L); below 9.5 because: -
