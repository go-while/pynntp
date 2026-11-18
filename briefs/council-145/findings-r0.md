# Round-0 findings on #145 (head 9b0db18), for the cross-check

From Luna: no findings (9.5).

From Sonnet:
- S1 (Low, new) scenarios.py:1618-1621 and :1730: the known_why fragments of three markers name only the exception class or row count: xzver/sync-flushed-not-finished ("expected a result, got NNTPDataError"), xzver/last-row-without-crlf ("expected 2 rows"), yenc/stray-yend-after-block ("expected a result, got NNTPYEncError"). Any other NNTPDataError/NNTPYEncError or wrong row set in those scenarios still counts as the known bug and stays xfail, hiding a different regression on that path.

From Haiku:
- H1 (Med, new) "positive controls" accept errors: Clean(...) makes judge_error (scenarios.py 2408-2415) return "" for any NNTPError/OSError, and probe=None means no state check. scenarios.py:1417-1424 compress/stream-finished-exactly: Clean(pred=v == PROBE_TUPLE): a regression that rejects a complete finished DEFLATE stream raises and passes (it is the positive control for compress/data-after-stream-end). scenarios.py:1616 xzver/data-after-deflate-end: Clean(pred=over_check): any clean error passes. scenarios.py:1805 post/early-441-then-close: Err(*CLEAN_ERRORS): passes on EPIPE without the 441 surfacing. Fix: Ok(PROBE_TUPLE) and Ok(pred=over_check) for the first two; Err(nntp.NNTPTemporaryError, match="441") for the third.
- H2 (Low, new) judge_value (2439-2442) skips the state check for Clean-with-value, while Ok rejects "late-broken" (2448-2450); leftover/crlf-after-terminator (923) therefore passes whenever the next command gets any clean error. Align the rule or document it.
- H3 (Low, new) loose known_why: same as S1 (1619, 1620).
- H4 (Low, new) server mismatches are not failures unless opted in: run() (2653-2698) ignores summary["mismatches"]; only 7 definitions use no_mismatch. The fake server answers unexpected lines with "500 unexpected" and keeps waiting, so a wrong command passes probe-less clean-error scenarios.
