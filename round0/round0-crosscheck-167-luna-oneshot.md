## Findings

1. **Low — `tests/integration/inn2/test_inn2.py:409`** — The empty-group test accepts *any* `high < low`, not just the RFC-permitted `high == low - 1`. An implementation returning an impossible empty-group range such as `(total=0, low=3, high=1)` passes. **Confirmed by reading; new.** S1 and H1 are the same finding.

2. **Low — `tests/integration/inn2/test_inn2.py:446`** — `test_xover_full_field` calls `xover()` but gates on the `OVER` capability. On another server, a server that advertises `OVER` but does not implement legacy `XOVER` fails instead of skipping; one that implements `XOVER` without advertising `OVER` skips a runnable test. **Confirmed by reading; new.**

3. **Low — `tests/integration/inn2/test_inn2.py:598`** — `test_from_url` now always supplies a port. With default settings, the real-server integration test no longer exercises `from_url` choosing its default port for `nntp`/`nntps`; that behavior was exercised before this change. **Confirmed by reading; new.**

4. **Low — `tests/integration/inn2/test_inn2.py:438`** — The default INN run now sends `NEWNEWS` a single group instead of the prior `local.*` wildmat. The test still checks retrieval for its posted article, but no longer exercises wildcard matching on the default path. **Confirmed by reading; new.**

5. **Low — `tests/integration/inn2/test_inn2.py:571`** — The refused-login test always tries the literal `user`/`secret`, even when `PYNNTP_USER`/`PYNNTP_PASS` configure those as accepted credentials. In that valid configuration, login succeeds and the test fails at `pytest.raises`. **Confirmed by reading; new.**

## Round-0 cross-check

- **S1:** Confirmed; see finding 1. It triggers when the client reports an empty group with a gap larger than the permitted one.
- **S2:** Confirmed; see finding 2. It triggers on another server whose `OVER` capability and `XOVER` command support differ.
- **S3:** Confirmed; see finding 3. It triggers on the default path, which no longer exercises URL-scheme default-port selection against the live server.
- **H1:** Confirmed; duplicate of S1.
- **H2:** Confirmed; see finding 4. It triggers on the default INN path, which no longer tests the `local.*` wildmat.

**Notes:** No style or preference-only issues noted. I did not run tests or builds; this is a reading-only review. `pr-text.md` was not found in the checkout.

**Score: 8.8/10.** Below 9.5 because the empty-group assertion accepts invalid results, and the default path loses the prior wildcard and URL-default-port integration coverage; configurable credentials also break the refused-login test for a valid configuration.

#167: 8.8, 5 findings (H/M/L): empty-group range, XOVER gate, URL default ports, NEWNEWS wildcard, refused login creds
