# Round-0 cross-check, PR #167 (hk-r0-haiku-167)

Head 54cb6e0, checked by reading the clean checkout (council-167/checkout) and nntp/nntp.py. Nothing run here (G1). The test-host numbers from the lead (host 117) are not verified by me.

Correction to my earlier report: finding 1's location was written garbled in the handback (a garbled path). The correct path is council-167/checkout/tests/integration/inn2/test_inn2.py:402-409.

## Other reviewers' findings

| ID | Sev | Verdict | Check at 54cb6e0 | Triggers when | Changes score? |
|----|-----|---------|------------------|---------------|----------------|
| S1 (= my H1) | Low | Confirmed | test_inn2.py:409 `assert high < low or (low, high) == (0, 0)`. Any high below low passes, including impossible shapes like (5, 3), and (0, 0, 0) from any client bug. The default INN run used to assert the exact (0, 1, 0). I did not verify from the RFC text (no web) whether high < low-1 is ever a valid empty form; the code accepts it either way. | Default INN run and any other server: a client or server that reports junk (or another empty group) as a wrong empty shape passes. | No, Low. Fix: on the default path assert (0, 1, 0); other servers may use high == low - 1 or all zeros. |
| S2 | Low | Confirmed | test_inn2.py:445-449: gated on `require_listed("OVER")`, but the body calls `nntp_client.xover(...)`, and nntp.py:1659 sends the XOVER verb (xover() is `_xover(range)` with the default verb "XOVER"; over() sends OVER at nntp.py:1731). | Only on another server (PYNNTP_HOST set): a server that lists OVER but not XOVER (RFC 3977-only) fails the test with a 500 instead of passing or skipping. A server with XOVER but no OVER in CAPABILITIES skips needlessly. Default INN lists and supports both, so no effect there. | No, Low; it is a wrong verdict on another server. Fix: call over() when OVER is listed, or gate on XOVER. |
| S3 | Low | Confirmed | test_inn2.py:597-603 (test_from_url): the URL always carries an explicit port, `f"{scheme}://{HOST}:{port}"`. The old `nntp://localhost` and `nntps://localhost` exercised the scheme's default ports (119, 563) against the live server. test_from_url_with_options (:606-609) also passes the port. | Every run, including default INN CI: the scheme-to-default-port mapping is no longer checked against a real server (the unit tests with mocks still cover it). Default-path narrowing, same class as my H1 and H2. | No by itself, Low. It adds a third default-path narrowing to the fix list. |
| L1 | Low | Confirmed | test_inn2.py:569-571 (test_login_refused_keeps_connection) hard-codes `login("user", "secret")` and expects 481/483/502. On another server configured with PYNNTP_USER=user and PYNNTP_PASS=secret, valid credentials, the login succeeds, no NNTPReplyError is raised, and pytest.raises fails. | Only with PYNNTP_HOST set and those exact credentials. Default INN has no login (USER empty), so unaffected. | No, Low: wrong failure verdict under a valid configuration. Fix: use credentials that differ from the configured ones, or skip when they match. |

## Lead's test-host numbers (not verified by me)

Lead reports on host 117 (INN 2.7.3, no implicit TLS port): head 31 passed + 4 failed, base 30 passed + the same 4 failed; with PYNNTP_TLS_PORT=0, head 31 passed + 4 skipped. The four implicit-TLS tests match the code reading: test_nntp_client_with_ssl, test_tls_verifies_certificate_by_default, test_compress[SSLMode.IMPLICIT], and test_from_url[nntps]. They connect to port 563, which is refused on that host, and base fails them the same way. So the four failures are a host-configuration matter, not a head regression, and PYNNTP_TLS_PORT=0 is the right setting there. The counts are consistent with the code; I cannot confirm them without a run.

## Score

Score unchanged at 9 for head 54cb6e0. The five distinct findings are all Low, and all but S2 and L1 are default-path narrowings (S1/H1, H2, S3). The fix list is now those three default-path items plus S2 and L1, which are other-server only. No Med or High finding in any reviewer's list that I can confirm.

#167: 9, 5 findings (H/M/L): 0/0/5 - empty-group check relaxed (S1/H1); NEWNEWS wildcard narrowed (H2); from_url default ports no longer checked (S3); XOVER gated on OVER (S2); refused-login test fails with valid user/secret (L1)
