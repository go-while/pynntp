# Round 0 review: PR #172 (fix/163-header-unfold, head 1c083aa)

Reviewer: hk-r0-haiku-a (Haiku 5.5, round 0, read-only). Base: upstream/main 2bfca17.
Scope: #163, parse_headers() dropped the whitespace before a folded line (+ linear-time unfolding).
Commits: c6b040d (keep internal whitespace), 72ad63b (linear unfolding), 1c083aa (larger timing test).
Method: read head nntp/utils.py parse_headers (:182-218), nntp/headerdict.py HeaderDict.__init__/update
(the constructor takes an iterable of pairs), the callers in nntp/nntp.py (article :1505, head :1536), the
test diffs, and the base test_utils.py folding and stop-at-blank-line tests. Issue #163 read. No code run,
no host run.

## Findings

None found.

## Checked by reading (no finding)

- Folding: continuation lines are appended raw (`line.rstrip("\r\n")` keeps internal and trailing spaces), and
  the joined value is stripped once. "X-Text: one \r\n two" gives "one  two" (RFC 5322 2.2.3: only the CRLF is
  removed). Matches the new docstring. Covered by test_parse_headers_fold_whitespace and test_head_folded_whitespace.
- Linear time: each header keeps a list of pieces, appended in O(1), joined once. No quadratic join is left.
  Checked for the continuation path and the final construction.
- Stop at blank line: `break` on an empty line after rstrip consumes only the blank line, so the generator stays
  positioned at the body. test_parse_headers_stops_at_blank_line (base) still applies; article() relies on this
  (nntp.py:1505 then `_read_body(lines)`). Checked.
- HeaderDict construction: `HeaderDict(generator of pairs)` works (MutableMapping update over an iterable). Duplicate
  names: later value wins, as on base. Checked by reading headerdict.py.
- First line as continuation, or a line without ":", still raises ValueError; article() and head() wrap it in
  NNTPDataError (_data_errors). Unchanged from base.
- Callers: only nntp.py:1505 (article) and :1536 (head). Both pass decoded lines with or without CRLF; the
  rstrip handles both. No other caller in the tree.
- Base tests (test_parse_headers, test_parse_headers_continuation) still expect the same values; by reading the
  expectations hold on head (e.g. "Apple\tBanana\tCarrot", "Test Subject with continuation").

## Notes (not findings)

- test_parse_headers_many_continuation_lines asserts a wall-clock limit of 3.0 s for 500,000 continuation lines.
  It can fail on a slow or loaded test host without any defect in the code. Consider a count-based check (e.g.
  the time ratio between two sizes) or a larger limit. Test quality, not a pynntp defect.
- Header count is not bounded (a long header block of many short headers); pre-existing, not in this change.
- One concern (header folding, with the linear-time rewrite done in the same function). Three commits; the net
  diff is the single function.

## Did not check

- Real server headers with folded values containing non-ASCII, or the surrogateescape path (decode happens in
  _decode before parse_headers, unchanged).
- Behaviour of the timing test on the test hosts (no run here).

## Score

9.5 / 10 (ready as is, by reading). The only item is the wall-clock assertion in the new test (note above).
