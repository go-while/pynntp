# Council #167 round 2: hk-council-opus-167r2 (Claude Opus 5.5, by reading)

Head 090f7ec, delta fdd9408..090f7ec (CONTRIBUTING.md, tests/integration/inn2/test_inn2.py).
Rules hash check in the rules: OK. Nothing was run, by reading only (G1). I checked
that `git diff --stat fdd9408 090f7ec` in the repo matches the patch (2 files, +49/-20).

## Round-1 findings

| # | Finding | Verdict | Evidence (head) |
|---|---------|---------|-----------------|
| 1 | Med: gating capabilities read before login | Fixed | test_inn2.py:144-152 reads CAPABILITIES, and if PYNNTP_USER is set and the server offers `AUTHINFO USER` (offers_login, :124-129) it calls login() and adds the lines read after the login. If MODE READER already got a 480, _connect logs in (nntp.py NNTPClient._connect), the server stops offering AUTHINFO, and the first list is already the post-login list. Keeping the pre-login lines keeps STARTTLS for test_nntp_client_with_ssl_starttls and the nntp+starttls from_url case. Default run: USER is "", so nothing changes. |
| 2 | Low: refused login leaves the wrong credentials | Fixed | login() stores the given username and password before sending them (nntp.py:765). test_inn2.py:611 puts USER/PASSWORD back after the pytest.raises block and before date(), so a 480 on date() logs in with the configured login. If login() unexpectedly succeeded, the pytest.raises block fails the test before that line, which is correct. |
| 3 | Low: stock INN groups demanded with PYNNTP_GROUPS | Fixed | CUSTOM_GROUPS (:86) is true when PYNNTP_HOST or PYNNTP_GROUPS is set. check_newsgroups (:110) then checks LIST ACTIVE for the configured groups. With neither set it checks exactly DEFAULT_NEWGROUPS, as before, so the default run is unchanged. |
| 4 | Low: IPv6 literal unbracketed in URLs | Fixed | URL_HOST (:91) brackets a host that contains ':' and is not already bracketed. It is used at :643 and :651. urlsplit's `.hostname` strips the brackets again, so from_url connects to the bare literal. Default "localhost" is unchanged. |

## New problems from the delta

Nothing found.

What I checked:
- Default INN run (no PYNNTP_* apart from TLS_CAFILE in check.yml): USER is empty, CUSTOM_GROUPS is False and URL_HOST is "localhost", so every changed path behaves as at fdd9408.
- The compress() refactor (:298-300) does the same as the old inline code.
- No new credential exposure. capabilities() sends AUTHINFO only where the server offers AUTHINFO USER on that connection, and the plain COMPRESS test already did that at fdd9408. The client keeps AUTHINFO arguments out of error text (nntp.py _command `shown`).
- Gated tests that now run on a login-only server (NEWNEWS, IHAVE, XPAT, HDR/OVER) get a 480 on their own unauthenticated connection, and the client logs in and retries. COMPRESS tests log in first. No new hang path.
- Errors from login() inside capabilities() (481 wrong password, etc.) raise, so a bad configuration shows up as an error rather than a silent skip.

## Notes (not findings)

1. A server that breaks RFC 4643 3.1 by still listing `AUTHINFO USER` after a 480-triggered login in _connect would make capabilities() send a second login. A 502 there raises, and every gated test errors. That needs a non-compliant server, and it fails loudly rather than skipping.
2. The `except NNTPPermanentError` at :153 now also covers login(). A 500 to AUTHINFO on another server would return () and silently skip every optional test. This is implausible right after AUTHINFO USER was advertised.
3. This is pre-existing, not in the delta. On a remote INN (PYNNTP_HOST set, is_inn() true), test_article_in_empty_group (:423-438, via empty_group :208-213), test_list_active[junk] (status "n") and test_post_to_junk_is_refused still assume a stock `junk`: empty, status n, posting refused. INN needs a junk group, but a production server's junk need not be empty or "n". CONTRIBUTING's new "a remote INN needs no stock groups" is true for local.* and control.*, not for these junk assumptions. PYNNTP_EMPTY_GROUP covers the empty-group test only. This could go on the issue list or get one doc sentence.
4. A scoped IPv6 literal (fe80::1%eth0) would need `%25` in a URL. That is an edge case, not a documented configuration.

## Not checked

No runs (G1). I took the lead's test-host results on trust. I did not re-review parts of the file outside the delta, apart from note 3.

## Score

9.5. All four round-1 findings are fixed, the delta adds no finding, and the default run is unchanged. Note 3 is pre-existing and Low at most.

#167 r2: 9.5, 0 findings (H/M/L): -
