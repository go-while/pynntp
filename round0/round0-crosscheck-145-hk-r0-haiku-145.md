# Round-0 cross-check, PR #145 (head 9b0db18), reviewer hk-r0-haiku-145

Scope: S1 from Sonnet (the finding not mine), against the same checkout
(council-145/checkout). Read only; nothing was run (G1). Other reviewers' reports
were read only in findings-r0.md, as asked.

## S1: loose known_why fragments (Sonnet) - CONFIRMED, Low

- scenarios.py:1618-1621 (xzver): "expected a result, got NNTPDataError" on
  sync-flushed-not-finished, and "expected 2 rows" on last-row-without-crlf. Any
  NNTPDataError on the first, or any wrong 2-row result on the second, stays
  XFAIL. This is my H3, same lines.
- scenarios.py:1730 (yenc/stray-yend-after-block): known_why
  "expected a result, got NNTPYEncError". judge_error (2408-2414) builds
  "expected a result, got <type>: <msg>" for any CLEAN_ERRORS exception when the
  expectation is Ok, so this fragment matches any NNTPYEncError from that body.
  NNTPYEncError is also raised for a CRC or size mismatch (nntp/nntp.py:1494,
  1557 docstrings; 1471 for bad data), so a decode regression on the valid block
  in that scenario would be masked as the #159 bug.
- Is the yenc marker too broad too: yes, by the same mechanism. It is narrower
  than the xzver pair, because this scenario has one error source, the valid
  block plus one stray =yend, and the yenc/crc-mismatch and yenc/size-mismatch
  scenarios (Err expectations, unmarked) still fail on a CRC regression. The
  hole is limited to the stray-yend scenario itself. Severity stays Low.
- Fix (same for all three): match the wrong value the bug produces, not the
  exception class, and check it against the failing output on a test host.

## Effect on my round-0 report

- No change to my findings or score: S1 is my H3 (Low), and the yenc marker
  adds one more instance of it, which I would now list with it.
- The lead's run result (host 116, host-built nntp-fakeserver v0.13.0: 220 passed,
  8 xfailed) is consistent with my reading. 8 xfailed matches the 8 known=
  scenarios, and nothing in it contradicts the verdict analysis. A passing run
  does not test sensitivity to regressions, which is what F1 (Med: the positive
  controls compress/stream-finished-exactly, xzver/data-after-deflate-end,
  post/early-441-then-close accept any clean error) and F4 concern. Those stand.

## Score

8.5 (unchanged). The 9.5 target needs F1 fixed (Ok on the two controls, a real
match for the 441 case), F2 and F3 (the state rule for Clean-with-value, and the
known_why fragments, including the yenc one at 1730), and F4 (mismatch
enforcement or allow list).

#145: 8.5, 4 findings (0/1/3): Clean controls accept errors (stream-finished-exactly, xzver/data-after-deflate-end, post/early-441); Clean skips state check; loose known_why (xzver 2 rows and NNTPDataError, yenc stray-yend NNTPYEncError); server mismatches not enforced
