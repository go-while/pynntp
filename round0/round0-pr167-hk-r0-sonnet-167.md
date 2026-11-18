# Round 0, PR #167, head 54cb6e0, reviewer hk-r0-sonnet-167 (Sonnet 5.5), by reading only

Read: the diff, the whole head test file, CONTRIBUTING.md, nntp/nntp.py (constructor, from_url, _command, capabilities), headerdict.py, check.yml, setup.sh, unit tests for default ports and from_url. Checked the default path (no PYNNTP_* set) line by line against the base. gh pr checks 167: all green (ruff/pre-commit, test-inn2 included).

## Default path (INN, no PYNNTP_*)
Unchanged where it matters. client() gives the same host/port/use_ssl/ssl_mode as the old calls for plain, implicit and STARTTLS. username="" and password="" are the constructor defaults, so no login. OTHER_SERVER is False, so require_listed, require_inn and skip_or_fail never skip, and is_inn()/capabilities() are not called from check_newsgroups. The XHDR asserts moved to test_xhdr with the same values and 500 still fails. The TLS default-verification test still fails if pynntp stops verifying: CI's self-signed cert is rejected by the stdlib probe, then pynntp must raise. The new `require` (first word equal, other words present) matches INN's COMPRESS DEFLATE, STARTTLS, IHAVE, NEWNEWS and XPAT lines as before.

## Findings

1. Low, tests/integration/inn2/test_inn2.py:406-410 (test_article_in_empty_group), new. The default-path assertion got weaker and the RFC claim is wrong.
   - Before: `group("junk") == (0, 1, 0, "junk")`. Now: `(total, name) == (0, group)` and `high < low or (low, high) == (0, 0)`.
   - A client bug that returns zeros (0, 0, 0) for INN's `0 1 0` passed no test before and passes now.
   - RFC 3977 6.1.1.2 (checked): the three forms are (1) high = low - 1, count 0, the only form with high < low; (2) all zeros; (3) high >= low, count zero or non-zero. The comment ("or a high water mark below the low one") and the PR text list "high below low" as the third form. That is not RFC form 3. The test accepts e.g. 5/3 (no form allows it) and fails a server that uses form 3.
   - Confirmed by reading and the RFC. Fix: assert `high == low - 1` (INN gives exactly that), or all zeros, and drop "high below low" from the comment and PR text. If form 3 matters, accept `total == 0` only when the 420 check also passes.

2. Low, test_inn2.py:~440 (test_xover_full_field) `require_listed("OVER")`, new, other servers only. The test calls XOVER, not OVER. A server with OVER but no XOVER fails the test (500), not skips. A server with XOVER but no OVER capability skips, so XOVER goes untested. Default INN is unaffected. Fix: skip on a 500 answer to xover, as test_xhdr does, or require nothing and handle the 500.

3. Low, test_inn2.py:588-600 (test_from_url) and `client()`, new, default path. The URL now always carries the port (`nntps://localhost:563`), and every other client call passes the port explicitly. The integration run no longer tests the default-port choice (nntps gives 563, nntp and nntp+starttls give 119, `NNTPClient("localhost")` gives 119) against a real server. Unit tests cover it with mocks (tests/test_connection.py test_default_port, tests/test_from_url.py test_schemes), so this is low. Fix: leave the port out of the URL when PORT/TLS_PORT equal the defaults.

No credential leak found. PASSWORD is a module global, so tracebacks (even with -l) don't show it. The URL has no password. Skip reasons print only codes. The PR's cleartext-over-119 login is the user's own config and documented in the client.

No hang or flake found that is new. The probe has a 10 s timeout and the client has a 30 s default. The Xref loop is bounded by POST_WAIT.

## Notes (not findings)
- test_newnews: pattern `"local.*"` became `GROUP` (a single group). The wildcard form is no longer exercised. Needed for other servers, but could stay `local.*` on INN.
- OTHER_SERVER is "PYNNTP_HOST is set at all". `PYNNTP_HOST=localhost` pointing at INN turns every missing-feature failure into a skip. Documented, but a hazard for anyone who exports it in a CI that tests INN.
- On a server without Xref in HEAD, every posting test skips (test_post, test_article, newnews, compress, xpat, hdr...). That is by design and documented, and -rs shows it. It is most of the suite.
- test_list_active compares group() to LIST ACTIVE high/low, which races with other posters on a busy shared server. Pre-existing, but more exposed now.
- test_from_url builds `nntp://HOST:PORT`, which breaks for an IPv6 literal HOST (needs brackets). Edge.
- ruff SIM105 might want `contextlib.suppress` in test_tls_verifies_certificate_by_default (try/with/except pass). CI is green, so not an issue.
- The "Xref lists the group but is not yet listed" case used to fail at once (KeyError) and now waits POST_WAIT and then raises AssertionError. Documented.

## Not checked
No runs (guard G1). No run against a non-INN server (OpenUsenetServer), against INN 2.8 or with credentials. I did not check INN's exact CAPABILITIES lines for LIST ACTIVE.TIMES, HDR or OVER (assumed from RFC 3977 and INN docs). I did not check whether InterNetNews CI or other external users set PYNNTP_HOST. Format (ruff format) was only checked for line length: none over 88.

## Score
9 of 10. Held below 9.5 by finding 1 (weaker default-path assert and the RFC misreading in code, docs and PR text) and by finding 2, a skip/fail verdict that is wrong for servers with XOVER but no OVER. Both are small. With them fixed I would give 9.5 or more.

#167: 9, 3 findings (0H/0M/3L): empty-group assert weaker and RFC form 3 misread; xover test gated on OVER not XOVER; explicit ports hide default-port coverage
