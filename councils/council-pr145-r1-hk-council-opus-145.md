# Council round 1: PR #145 (fault-injection tests), head 88a97b1

Reviewer: hk-council-opus-145 (Claude Opus, fresh). Base 2bfca17, head 88a97b1.
I checked that /etc/agents/HASH.md matches. Locally I only read files and ran git and gh (read-only).
I did one run on a test host through vm-run.sh/jobq.sh (job 359 on 10.10.11.106).

## What I did

- Read the whole diff: faults.yml, .gitignore, CONTRIBUTING.md, tests/faults/README.md,
  conftest.py, test_faults.py, and all of scenarios.py (runner, verdict logic and all 17 scenario
  families).
- Read the nntp-fakeserver v0.13.0 source from the Go module cache (cmd/nntp-fakeserver/raw.go,
  main.go, fakeserver Endless/Deadline/auth). I checked how the server handles raw-mode Expect
  (an anchored regexp), mismatches ("500 unexpected", plus every line after the script), notes,
  the Deadline, Endless, and which commands are exempt from 480 (MODE and DATE are).
- Checked each `known=` marker on GitHub (read-only). #154, #157, #159, #160, #161 and #162 are
  open issues. Their fix PRs #168, #170, #171, #173 and #187 are open. I read the diffs of
  #170, #171 and #173, and the parts of #168 and #187 that raise errors:
  - yenc/stray-yend: #170 ignores a stray =yend when no text was dropped, so the scenario returns
    the data and shows XPASS.
  - xzver/last-row: #171 yields the last row, so XPASS.
  - malformed/group-negative: #173 raises NNTPDataError, which is what the scenario expects, so
    XPASS.
  - session/resume: #168 raises NNTPSyncError, which attempt() catches, so the predicate passes:
    XPASS.
  - leftover/*: #187 raises NNTPProtocolError, a clean error with Clean and probe=None, so XPASS.
  - The known_why fragments match the error texts in the current code: nntp.py:565 and
    yenc.py:92.
- Checked that the SHA for actions/setup-go is the v7.0.0 tag
  (b7ad1dad31e06c5925ef5d2fc7ad053ef454303e).
- Test-host run on a scratch copy with one patch: judge_error fails any scenario whose error was
  accepted while the probe state was "late-broken". The run also counted scenario names.
  Result: 228 scenarios, 228 unique names, 220 passed, 8 xfailed (strict), 108 s. No scenario
  depends on the late-broken acceptance described in finding 1.

## Findings

| # | file:line (88a97b1) | What goes wrong, when | Sev | Confirmed | New |
|---|---|---|---|---|---|
| 1 | tests/faults/scenarios.py:2430-2455 (judge_error), with probe_state 2408-2427 | When an action raises a clean error and the expectation is `Err(state="any")` or `Clean`, the scenario passes with state "late-broken". Late-broken means the action left the connection unmarked and the DATE probe then failed on leftover bytes, i.e. the connection was out of sync. The README (and the PR text) says an error passes only if the connection is "still in sync ... or marked broken (the next command raises NNTPSyncError)". Late-broken is neither. Late-broken results are refused only for Clean results (judge_clean), not for errors. Trigger: a regression in an error path that stops reading a block early without marking the connection broken. Example: xzver/bad-crc, bad-size or missing-trailer, malformed/over-nonnumeric-row or article-bad-header-line raising before the "." terminator. The probe then reads "." or a data line, gets NNTPProtocolError (which marks the connection broken), and the scenario passes. That is the #161 class of bug the suite is meant to catch. Today no scenario relies on this: with late-broken refused for errors, all 220 still pass. So the fix costs nothing: in judge_error, refuse `state == "late-broken"` (or allow it only with an explicit opt-in, as `Clean.late_broken` does for results). | Low | Reading + test-host run (job 359) | yes |

I found no other defect that meets the "Findings" test.

## Notes (not findings)

- post/early-441-then-close (scenarios.py ~1820): the comment says "the server check (no
  unexpected client lines) covers what it sent". The step closes right after the POST line, so the
  raw handler never reads anything after it. The check covers nothing here, and the comment
  overstates it.
- The server's `notes` (e.g. "starttls: N bytes of plaintext pipelined", "dot block read: ...")
  are never looked at. Today any such case also fails on the client side.
- `mismatches` are checked only when the reason is empty, so a known scenario ignores them until
  its fix lands. That is fine (a mismatch then fails the run instead of showing XPASS).
- The child runs with `python -I` and imports the installed `nntp`. With uv's default editable
  install that is the working tree. A non-editable install would test the installed copy instead.
- Leftover and session known scenarios use `Clean` with probe=None, so after the fix any clean
  error passes without a state check. This is deliberate, and the fix PRs bring their own unit
  tests.
- If the server hangs and is SIGKILLed, its own temp directory (CA files) stays in /tmp. This
  happens only after a server hang, which the run reports anyway.
- `scenarios()` says "names are unique" but nothing enforces it. Today they are (228/228). A
  duplicate would make the child run a different scenario than the server was given.
- Workflow: contents:read, no secrets, only workflow_dispatch and schedule. Actions are pinned by
  SHA. go install @tag is pinned by sum.golang.org. Go setup has no cache. Nothing to report.

## Not checked

- I did not run the workflow on GitHub Actions (ubuntu-26.04, Python 3.15/3.15t, free-threaded
  builds without the memory limit). I did not run ruff or mypy on the suite (the lead reports they
  pass).
- I did not run the fix PRs against the suite to see XPASS happen. That is based on reading their
  diffs; for #168 and #187 only the parts that raise errors.
- I did not check flakiness by repeated runs. One run only, on a 1-core container. I checked the
  timing margins by reading (smallest: line delay 400 ms against a 1 s timeout; drip 30 ms per byte
  against a 1 s timeout).
- I did not review nntp-testkit itself beyond the behaviour the scenarios rely on.

## Score

9.5. The suite is careful. Verdicts are strict for Ok results and for state="sync"/"broken". The
known markers are pinned to their wrong outcome, xfail is strict with raises=AssertionError, and a
server-side problem in a known scenario fails the run. The marker for each open bug turns into
XPASS when its fix lands. Finding 1 is a latent gap in the verdict, which no scenario hits today,
and a one-line fix. It doesn't keep the score below target, but it should be fixed so the code
matches the documented rule.

#145: 9.5, 1 findings (0/0/1): judge_error accepts late-broken (desynced) connections after clean errors
