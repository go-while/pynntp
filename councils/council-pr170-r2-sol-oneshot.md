I’ll keep this review read-only. I can’t verify the `/etc/agents` hashes or ownership with the permitted tools; I won’t run any commands or tests.
**All three round-1 findings are fixed.**

1. **Whitespace data — fixed.** `nntp/nntp.py:1500` treats spaces as dropped data; the supplied input raises `NNTPYEncError`. Regression test: `tests/test_articles.py:185`.
2. **Duplicate trailer after signature — fixed.** `_stray_yend_error` accepts a trailer matching the closed block (`nntp/nntp.py:191`), preserving `b"A"`. Regression test: `tests/test_articles.py:199`.
3. **Docstring — fixed.** `nntp/nntp.py:1466–1477` describes the correct interval and lists the outside-block error.

**New findings: none independent of already-tracked defects.**

**Notes**
- The new helper exposes another route to the known T3/S6 oversized-decimal bug: after a complete block and signature, `=yend size=` followed by 5,000 digits reaches `nntp/yenc.py:91`, raising raw `ValueError` before draining the response under Python’s default digit limit. Already tracked; not counted again.
- Confirmed by reading only. No commands or tests were run; unrelated code was not reviewed.

**Score: 9.5/10** for this round’s scoped delta.

#170 r2: 9.5, 0 findings (H/M/L): -
