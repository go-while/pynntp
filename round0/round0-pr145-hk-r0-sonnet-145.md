# Round 0 review of pynntp #145 (hk-r0-sonnet-145, Sonnet 5.5, by reading only)

Head 9b0db18, base 2bfca17. Nothing was built or run (G1). the rules hashes matched.

## Findings (1)

| # | Sev | Where | What | Confirmed | New |
|---|---|---|---|---|---|
| 1 | Low | tests/faults/scenarios.py:1618-1621 (known_why of xzver/sync-flushed-not-finished: "expected a result, got NNTPDataError"; xzver/last-row-without-crlf: "expected 2 rows"), :1730 (yenc/stray-yend-after-block: "expected a result, got NNTPYEncError") | The known_why fragment names only the exception class or the row count, not the bug's own message ("compressed data is truncated", the stray =yend). Any other NNTPDataError / NNTPYEncError / wrong row set in these three scenarios still counts as the known bug and stays xfail, so a different regression on the same path is hidden there. Sibling scenarios (xzver/bad-crc, bad-size, finished; yenc/crc-mismatch, single) cover most of it, so the exposure is small. The leftover/*, session/* and group-negative-numbers fragments are specific enough. | by reading | yes |

## Checked and found right

- Runner (run, run_client, run_client_process, server_json): the child is killed on timeout by subprocess.run; the server is stopped by closing stdin and killed if it does not exit within 10 s; Popen's context manager closes the pipes, so the server exits on EOF and nothing leaks on an exception. No credentials beyond the fake u/p. The child runs with `-I`, a 1 GiB RLIMIT_AS (not on free-threaded builds), and its stdout is filtered to the JSON line.
- Verdict logic: a desync is checked before anything else and applies to Ok, Err and Clean. An Ok result with a probe needs state "sync". Err(state="sync") needs a probe (checked in __post_init__). Err(state="broken") on a probe-less scenario is probed anyway, and "late-broken" fails it. The stale DATE (2099) and the exact 2020 reply make the probe real. Server-side problems (no summary, exit status) are added to the reason, and server_check runs only when the client side passed.
- test_faults.py: xfail(strict, raises=AssertionError) plus pytest.fail (a Failed, not an AssertionError) for a server-side problem or a reason that lacks known_why. A known scenario that passes is XPASS(strict) and fails the run. Checked against the fix PRs: #168 (next() on the old iterator raises NNTPSyncError, so the Clean pred passes), #170 (a stray =yend without dropped text is ignored, so Ok(data)), #171 (last row kept, so over_check passes), #173 (NNTPDataError "Invalid GROUP", state stays sync), #187 (refuses the next command while data is unread: the Clean pred of the 3 leftover scenarios passes on an error). Each of the 6 marker groups matches an open issue (#154, #157, #159, #160, #161, #162 all open) and would XPASS when its fix lands.
- known_why strings match the reason texts the runner generates ("expected a result, got ...", "wrong result ..., expected 2 rows", "expected NNTPDataError, got result", the Clean desc texts).
- Workflow: workflow_dispatch plus weekly schedule only, permissions contents: read, no secrets, no pull_request trigger. The 3 action SHAs resolve to the named tags (checkout v7.0.1, setup-go v7.0.0, setup-uv v10.3.3). `uv sync --locked`. The matrix matches check.yml. nntp-fakeserver is pinned by tag v0.13.0 (tag exists, 8a7ab18; go.mod needs go 1.26.0, setup-go gets 1.26.x). The install goes to $RUNNER_TEMP. Same tag in README.
- Against the testkit v0.13.0 source: Expect is an anchored regexp; a non-matching line gets "500 unexpected" and is a mismatch (so scenarios that omit no_mismatch still see it as a client error); MODE READER is not 480 on a store with User/Pass, so the auth/480-once-on-* line_sequence (login, cmd, login, cmd) holds; "any 480 on an authenticated connection ends its login" matches the "mid-session 480" design; OverrideTimes counts per connection; LongLine is N "x" bytes without CRLF, so limit-2 is exactly 64 KiB with CRLF; RawStall accepts and never writes (tls-handshake-stall needs no tls option).
- Stateful Deflate objects in the compress scenarios are used in argument order (BODY step before DATE step), so the stream stays continuous; the child's rebuilt copies are never sent.
- The three probe-less scenarios whose script still has a DATE step (leftover/*, timeout/*) are harmless: the step is unused or matches the client's own date().

## Notes (not findings)

- known_strict is never set to False; the field is dead.
- scenarios() says "names are unique" but nothing enforces it, and the child takes the first match by name. I found no duplicate (literal names by grep, loop-built names by reading), so no trigger.
- XPASS shows only in the opt-in workflow (weekly or manual). The fix PRs (#168, #170, #171, #173, #187) run check.yml only, so the PR that lands second has to remember the markers (documented in the PR text and the README, not enforced).
- #154's issue text says the strict rejection may be intended and needs a decision. The marker encodes "must accept"; if the decision is to keep rejecting, the scenario has to be rewritten instead of its marker removed.
- post/store-ok filters "." lines out of the received article before comparing the last two lines, so it does not check the terminator count; ihave/peer-* have no sync probe (the peer mode has no DATE).
- The child imports `nntp` under `-I`, so the package must be installed (uv sync does that, editable). A parent that imports from the working tree while the child uses another installed copy is possible only without uv sync.
- The CI cache (enable-cache) is the same as in check.yml.

## Not checked

- Nothing was run. I did not confirm that any of the ~228 scenarios passes or fails on pynntp 3.3.0; in particular the observed-behaviour pins (malformed/status-code-only, text-before-autodetect, data-after-deflate-end, leftover/crlf-after-terminator "ends marked broken", compress/store-480-after-compress, the drop-after-N counts of the store) rest on the author's runs.
- I read about 80 percent of scenarios.py line by line (runner, verdict logic, split, code, leftover, drop, timeout, tls, compress, gzip, xzver, yenc, post, ihave, auth, malformed, session, longline); I only skimmed the store-based compress scenarios and the test helper builders for byte-level correctness (yenc_lines, xz_payload).
- The diff of #187 was not read, only its title; the testkit was read only where named above.
- ruff, mypy --strict and pytest of the default run were not run.

## Score

9: no blocker and one Low finding; nothing was run, and the suite's own pass/fail on a test host has to confirm the observed-behaviour pins. The one Low finding (narrow known_why) is what keeps it below 9.5 together with the unrun status.

#145: 9, 1 findings (0H/0M/1L): known_why of 3 markers too broad (xzver/sync-flushed, xzver/last-row, yenc/stray-yend)
