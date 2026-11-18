## Findings

1. **`tests/faults/scenarios.py:1420`, `:1616`, `:1808` — permissive expectations let regressions pass.** In `compress/stream-finished-exactly` and `xzver/data-after-deflate-end`, `Clean` accepts any `NNTPError`/`OSError`, even when its predicate requires a specific successful result. In `post/early-441-then-close`, any such error passes, including an `EPIPE` before the client observes the intended 441. **Med** — confirmed by reading; new.

2. **`tests/faults/scenarios.py:928-932`, `:2439-2442` — `Clean` skips the connection-state check on successful results.** `leftover/crlf-after-terminator` can return the expected body, then have the DATE probe fail and mark the connection broken only during the probe; `judge_value` still passes it. That misses the scenario’s stated requirement that the connection state be checked. **Low** — confirmed by reading; new.

3. **`tests/faults/scenarios.py:1618-1620`, `:1730` — known-failure reasons are too broad.** For the XZVER markers, any `NNTPDataError` or any wrong result described as “2 rows” matches the known reason; for yEnc, any `NNTPYEncError` matches. A different regression on those paths can therefore remain xfailed instead of failing the run. The markers do name the corresponding open bugs, but their reason checks do not distinguish those bugs from other failures. **Low** — confirmed by reading; new.

4. **`tests/faults/scenarios.py:2687-2690` — server command mismatches are ignored unless a scenario opts in.** For example, `post/early-441-then-close` has no `no_mismatch` check and accepts any clean error. If a wrong client command receives the fake server’s “500 unexpected” response, the scenario can pass without testing the intended early 441 path. **Med** — confirmed by reading; new.

## Round-0 cross-check

- **S1 — Confirm.** The three `known_why` fragments check an exception class or generic row-count description, not the specific failure. A different error or wrong row set can trigger them and remain xfailed. **Low; triggers on those marked XZVER/yEnc scenarios.**
- **H1 — Confirm.** `judge_error` treats a clean error as success for `Clean`, and the cited scenarios do not require the intended result/error. A rejected complete DEFLATE stream, an XZVER error, or an early POST `EPIPE` can pass. **Med; triggers on those three scenarios.**
- **H2 — Confirm.** `judge_value` returns from the `Clean` branch before checking state. A correct body followed by a probe that only then marks the connection broken can pass `leftover/crlf-after-terminator`. **Low; triggers when that action returns the expected body but the probe yields late-broken state.**
- **H3 — Confirm.** This is the same loose known-failure matching as S1, not a separate issue. **Low; triggers on those marked scenarios.**
- **H4 — Confirm.** `run()` checks server exit and optional `server_check`, but does not fail on `summary["mismatches"]` generally. An unexpected command can therefore be overlooked in scenarios with permissive expectations and no mismatch check. **Med; triggers on such scenarios, including the cited POST case.**

## Notes

- The workflow uses pinned action SHAs, a pinned fake-server version, read-only contents permission, and does not expose secrets in the shown configuration; I found no workflow issue in the diff.
- I did not run the suite or CI: workstation rules prohibit tests here. The reported **220 passed, 8 xfailed** is the supplied test-host fact, not a run I verified. I also did not find `pr-text.md` in the checkout.

**Score: 8.0/10.** The false-positive expectations, skipped state check, broad xfail reasons, and unchecked server mismatches keep this below 9.5.

#145: 8.0, 4 findings (H/M/L): permissive expectations; Clean skips state check; loose known-failure reasons; ignored server mismatches
