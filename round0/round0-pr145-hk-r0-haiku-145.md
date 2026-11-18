# Round-0 review: pynntp PR #145 (head 9b0db18), reviewer hk-r0-haiku-145

Read-only review of tests/faults/ (scenarios.py, test_faults.py, conftest.py),
.github/workflows/faults.yml, and the README, CONTRIBUTING and .gitignore diffs.
Line numbers are for the clean head checkout at council-145/checkout.

Nothing was run (guard G1, read-only role). Read: the verdict and runner code,
the nntp library paths it depends on (status, _sync, _command, _unexpected,
quit, _connect, _MULTILINE), and the Go fake server's raw handler
(nntp-testkit v0.13.0: cmd/nntp-fakeserver/raw.go, main.go; fakeserver/server.go).
Upstream issue and PR states were read with gh (read-only).

## Findings

### F1 (Med, new): "positive controls" accept errors

- scenarios.py:1417-1424 `compress/stream-finished-exactly`: `Clean(pred=v == PROBE_TUPLE)`,
  probe=None. judge_error (2408-2415) returns "" for any NNTPError/OSError when
  the expectation is not Err, and needs_state() is False, so there is no state
  check either. A regression that makes the client reject a complete, finished
  DEFLATE stream (the #154 class, in COMPRESS) raises, and the scenario passes.
  This is the positive control for `compress/data-after-stream-end`, which is
  correctly Err(broken).
- scenarios.py:1616 `xzver/data-after-deflate-end`: `Clean(pred=over_check)`. Any
  clean error passes here too.
- scenarios.py:1805 `post/early-441-then-close`: `Err(*CLEAN_ERRORS)`, probe=None.
  The scenario passes on EPIPE/ECONNRESET without the 441 ever being surfaced,
  so it does not test the 441 its name names.
- Confirmed by reading. Who triggers it: any regression of the named path that
  turns success into a clean error. Fix: `Ok(PROBE_TUPLE)` for the first, an
  `Ok(pred=over_check)` for the second, and `Err(nntp.NNTPTemporaryError,
  match="441")` for the third.

### F2 (Low, new): Clean-with-value skips the state check that Ok applies

- judge_value (2439-2442) returns "" for Clean with a passing or absent pred and
  never looks at `state`. For Ok the same state is rejected (2448-2450: "result
  ok but the connection is ..."). So a successful result followed by a probe that
  ends "late-broken" passes Clean and fails Ok.
- Reached by `leftover/crlf-after-terminator` (scenarios.py:923): a stray CRLF
  after a complete body passes whenever the next command raises any clean error.
  That is every outcome the library gives for that line today, so the scenario
  cannot fail on this class of desync. Its comment says this is intended.
  Either apply the same state check to Clean-with-value, or say in the
  Clean docstring that a late-broken success is accepted.

### F3 (Low, new): two known_why fragments match more than the known bug

- scenarios.py:1619 `"expected a result, got NNTPDataError"` matches any
  NNTPDataError from xzver/sync-flushed-not-finished. 1620 `"expected 2 rows"`
  matches any wrong 2-row result of xzver/last-row-without-crlf (judge_value
  prints "wrong result ..., expected 2 rows" for any value that misses the
  predicate). A partial fix (say, a row with the wrong subject) keeps XFAIL green
  and the run green, with no XPASS.
- The README states this ("a different wrong result of the same kind still
  counts"), so it is a conscious trade-off. Fix: tighten known_why to the wrong
  value the bug produces, checked against the failing output on a test host by
  the lead.

### F4 (Low, new): server-side mismatches are not failures unless opted in

- run() (2653-2698) fails only on server_check output and on a missing summary or
  non-zero exit. Client lines the script did not expect are recorded in
  `mismatches`, and only 7 scenario definitions (lines 838, 850, 1169, 1776,
  1784, 1824, 2060) pass no_mismatch.
- The Go raw handler answers each unexpected line with "500 unexpected" and keeps
  waiting for the expected one (nntp-testkit cmd/nntp-fakeserver/raw.go:215-225).
  So a client that sends a wrong command still passes any probe-less scenario
  whose expectation is a clean error of any state (e.g. 1805). Most raw scenarios
  probe, which catches the 500 reply, so impact is Low.
- Fix: fail run() on a non-empty summary["mismatches"] for raw scripts, with an
  explicit allow list for any script that sends deliberately unexpected lines.

## Notes (not findings)

- marked_broken (2359-2367) sends a second DATE when the first probe failed
  cleanly on a connection not yet marked broken. It returns True only through
  the broken flag (NNTPSyncError at entry), so no wrong verdict. It costs up to
  the client timeout (5 s default) and sends an extra line to raw servers.
- scenarios.py:1604 `xzver/empty` pins Ok([]) for a reply with no yEnc block at
  all, so an empty or truncated XZVER body reads as zero rows. Library behaviour
  that the test only pins; worth a decision.
- scenarios.py:1518 `gzip/terminator-inside-trailer-late` pins open #155 as the
  expected outcome (Err(OSError, broken)). It is documented in the code and in
  the PR text. When #155 is fixed this fails hard rather than XPASS, so the fix
  PR must edit it. Acceptable if said in #155's PR text.
- faults.yml: nntp-fakeserver is installed from tag v0.13.0. Tags are mutable;
  the Go checksum DB guards a moved tag after the first fetch. Actions are
  SHA-pinned (setup-uv and checkout match check.yml), no secrets, read-only
  token, no pull_request trigger. checkout does not set
  persist-credentials: false (nit).
- Cost, not verdict: dot_line_payload() (1542) can try up to 200 seeds times 56
  line widths of zlib, and scenarios() is rebuilt in every child process (about
  230 times per run).
- run_client_process (2649): json.loads on a stdout line that starts with "{"
  but is not JSON raises a test error, not a false pass.
- Tightest "under the timeout" cases: split/store-linedelay-over-under-timeout
  (400 ms gap, 1 s timeout) and timeout/drip-under-timeout (about 0.6 s of drip,
  1 s timeout). Not flaky by reading; slow hosts are the risk.
- The fake server listens on 127.0.0.1:0 by default (cmd/nntp-fakeserver/main.go:173),
  so ports are random. Credentials are the static test pair u/p.

## Checked and fine

- The 8 known= markers each map to an open issue or PR (gh, read-only): issues
  #154, #157, #159, #160, #161, #162 are OPEN; fixes #168, #170, #171, #173, #187
  are OPEN. I traced each known scenario through judge_error/judge_value: when
  its fix lands the scenario takes the passing path, so XPASS strict fires.
  #155 (pinned, not marked) is also OPEN.
- test_faults.py: a known scenario with a server-side problem, a hang or a wrong
  reason goes to pytest.fail, not xfail. known_strict is never set to False.
- Runner cleanup: the Popen context closes the server's stdin on error; the
  server is killed when it printed no address, and after SERVER_WAIT; subprocess.run
  kills the child at the deadline. RLIMIT_AS is set only in the child, after
  scenarios() is built, and is skipped on free-threaded builds.
- A missing summary or a non-zero server exit fails the scenario.
- collect_ignore keeps the default pytest run from collecting the suite.

## Not checked

- Nothing was run (no tests, no test hosts).
- Go fake-server behaviour for each script; only the raw handler, the mismatch
  path and the listen address.
- Library behaviour only along the paths the verdict uses.
- probe="store" date assumptions against the fake server's DATE output.
- ruff/mypy on scenarios.py; the ubuntu-26.04 runner label.
- The action SHAs against the action repos (only that faults.yml matches
  check.yml).

## Score

8.5. Below 9.5 because of F1 (positive controls accept errors). To reach 9.5:
make the two Clean positive controls Ok and give the 441 case a real match (F1);
apply one state rule to Clean-with-value or document it (F2); tighten the two
known_why fragments (F3); enforce or allow-list mismatches (F4).

#145: 8.5, 4 findings (0/1/3): Clean controls accept errors (stream-finished-exactly, xzver/data-after-deflate-end, post/early-441); Clean skips state check; loose known_why (xzver 2 rows, NNTPDataError); server mismatches not enforced
