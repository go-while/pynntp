# Council round 2, PR #145 (fault-injection tests), head ae27409

Reviewer: hk-council-opus-145r2 (Claude Opus, fresh). Reviewed by reading only
(checkout-r2 at ae27409, delta 88a97b1..ae27409). No runs; no claim that tests pass.
Rules HASH.md verified OK.

## Round-1 findings

| # | Sev | Finding | Status | Where (ae27409) |
|---|-----|---------|--------|-----------------|
| 1 | Med | Server mismatches / server_check evaluated only when the client reason was empty, so a known scenario could XFAIL despite server-side problems | Fixed | tests/faults/scenarios.py:2732-2744 append "server side: ..." to any existing reason; tests/faults/test_faults.py fails a known scenario on any "server side:" via pytest.fail (not an AssertionError, so the xfail does not absorb it) |
| 2 | Low | judge_error accepted a clean error on a "late-broken" connection for Err(state="any") and Clean | Fixed | scenarios.py:2447-2449 (Clean), 2466-2469 (Err, all states; "sync"/"broken" were already refused by the earlier checks); Err gains late_broken (234-240); README 43-48 and docstrings updated |
| 3 | Note | post/early-441-then-close comment claimed server check covers the upload | Fixed | scenarios.py:1832-1835 |

## Did the delta add a problem?

Checked:
- Pass path unchanged: when the client reason is empty, the new code does exactly
  what the old did (mismatch, then server_check), so no known scenario loses its
  XPASS when its bug is fixed.
- Fail path: for non-known scenarios the server reasons are only appended (more
  detail, same verdict). For known scenarios a server-side problem now fails the
  run instead of xfailing, as round 1 asked. None of the 8 known scenarios
  (scenarios.py:901, 914, 927, 1658, 1768, 2153, 2318) depends on unexpected client
  lines for its known outcome; the lead reports the same 8 xfails.
- Hang / client-died paths: res lacks "state"/"result", but test_faults.py uses
  .get; a server_check on an empty summary only adds a reason to an already failing
  run.
- Late-broken refusal and flakiness: the only scenario documented as racy
  (post/early-441-then-close) has probe=None, so state is "n/a" and the new check
  cannot fire. The only scenario relying on late-broken (leftover/crlf-after-terminator,
  :942) is a Clean with late_broken=True and a result, unaffected.
- Err with state="broken" on a late-broken connection still reports the more
  specific "expected marked broken, it is late-broken" first; ordering is fine.
- No new processes, credentials or files.

Findings: nothing found.

## Notes (not findings)
- The late-broken message string is written twice in judge_error (Clean branch and
  Err tuple) and a third variant in judge_clean; a shared constant would avoid drift.
- Clean's docstring says "in sync or marked broken", but with probe=None no state is
  checked ("n/a"); pre-existing and documented in the README probe=None paragraph.

## Not checked
- No test-host run (optional; the lead reports 220 passed, 8 xfailed strict on
  nntp-fakeserver v0.13.0, full check green). Repeat-run flakiness of the new
  late-broken refusal on error paths was judged by reading only.
- Scenarios outside the delta were not re-reviewed.

## Score
9.5 for ae27409: all three round-1 items are fixed as described, the README matches
the code, and the delta introduces no new wrong verdict, unfailable scenario,
lost XPASS, hang or leak.

#145 r2: 9.5, 0 findings (0/0/0): -
