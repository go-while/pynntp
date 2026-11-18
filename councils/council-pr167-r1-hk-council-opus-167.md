# Council review, PR #167 round 1, hk-council-opus-167

Head fdd9408, base 2bfca17. Scope: tests/integration/inn2/test_inn2.py and
CONTRIBUTING.md. Rules checked: /etc/agents HASH.md matches (sha512sum -c OK).
Method: I read the code only (diff, the full head test file, nntp/nntp.py login, _command,
_connect, compress, from_url, CI workflow, setup.sh). I ran nothing, so this
review makes no claim that tests pass.

## Default path (no PYNNTP_*, INN on localhost, both CI jobs)

I checked each test against the base. The default run tests what it tested before:
- client() passes port 119/563 and username=""/password="", which are the
  constructor defaults. Implicit-vs-STARTTLS port selection matches the base's
  port=None behaviour, test_compress included.
- require_listed, skip_or_fail, the XOVER/XHDR 500 handling, require_inn and
  the CAPABILITIES 500 fallback all depend on OTHER_SERVER, so they never
  skip by default. Xref missing still fails; a Xref without the group now fails
  after POST_WAIT instead of failing at once with a KeyError.
- test_article_in_empty_group keeps the exact (0, 1, 0, "junk") check. The junk
  tests and check_newsgroups keep INN's default groups.
- The XHDR assertions moved from test_hdr_over_stat_listgroup into test_xhdr.
  Both forms are still asserted.
- test_newnews still uses "local.*" and test_from_url still uses URLs without
  a port.
- test_tls_verifies_certificate_by_default: the stdlib pre-check rejects the
  self-signed certificate (in both CI jobs it is not in the system store), so
  pynntp must still raise SSLCertVerificationError. This is the same verdict
  as before.
- The new require() matcher still matches "COMPRESS DEFLATE", "STARTTLS",
  "IHAVE", "POST", "NEWNEWS" and "XPAT" on INN's lines.

## Findings

1. tests/integration/inn2/test_inn2.py:583-590 (test_login_refused_keeps_connection).
   Low, new. Confirmed by reading nntp/nntp.py:755-766 and 701-731.
   Trigger: PYNNTP_HOST/PYNNTP_USER/PYNNTP_PASS against a server that wants a
   login but accepts MODE READER without one and answers 480 to later commands.
   INN with an auth-required readers.conf behaves like this.
   What goes wrong: login("user", <random>) gets 481, which the test now
   accepts. But login() has already stored the wrong credentials in the client
   (self.username, self.password = ...). The next date() gets 480, the client
   logs in again with "user"/<random>, gets 481, and NNTPReplyError fails the
   test. On such a server the 481 that the PR adds can only come back when the
   follow-up date() then fails.
   Wrong verdict: the test fails against a valid login server and says nothing
   about pynntp.
   Fix: after the refusal, put back USER/PASSWORD on the client (or log in with
   them), or run the refusal on a client that has no stored credentials.

2. tests/integration/inn2/test_inn2.py:94-114 (check_newsgroups), used by about 9
   tests (the client and context-manager tests, with and without SSL, STARTTLS,
   compress, from_url). Low, new. Confirmed by reading.
   Trigger: PYNNTP_HOST points at an INN server that setup.sh did not prepare,
   with PYNNTP_GROUPS naming its own test groups, and the server lacks
   local.general/local.test or has changed any of the 8 default descriptions.
   What goes wrong: because is_inn() is true, the check still demands INN's
   DEFAULT_NEWGROUPS. PYNNTP_GROUPS is ignored, and all of those tests fail.
   The docs only say a non-INN server needs PYNNTP_GROUPS listed; nothing says
   a remote INN must keep the stock local.* groups and their descriptions.
   Fix: when OTHER_SERVER is set, or when PYNNTP_GROUPS is set, check the
   configured groups, or document the requirement for INN.

## Notes (not findings)

- capabilities() is cached from a fresh connection. On a server that only
  asks for a login after MODE READER, it holds the pre-login list. If that list
  omits HDR/OVER/LIST ACTIVE.TIMES, those tests skip with PYNNTP_HOST set.
  This affects only the other-server mode; I have not seen a concrete server
  doing it.
- test_article_in_empty_group (other server / PYNNTP_EMPTY_GROUP) requires
  total == 0. RFC 3977 6.1.1.2 case 3 (high >= low) allows a non-zero estimate.
  Only a user-chosen group is affected; the code comment states the design.
- On an INN with PYNNTP_HOST and no PYNNTP_EMPTY_GROUP, "junk" is assumed
  empty. A production INN may have filed articles there, and then the test
  fails.
- test_login_refused sends a deliberately wrong login to a real remote server.
  Repeated runs could trip failed-login rate limits or bans there. This is
  speculative.
- test_from_url_with_options now has an explicit ":119". test_from_url
  ("nntp") still covers the default port, so no coverage is lost.
- test_xhdr: on another server, a 500 to the message-id form also skips the
  number-form result that already passed. This is minor.
- PYNNTP_USER/PASS go over port 119 in plain text unless TLS is used, as the
  library documents. CONTRIBUTING could say so. Credentials don't appear in
  test IDs or in assertion output: they are module globals, not locals of the
  test frames, and AUTHINFO is masked in error messages.

## Not checked

- I did no runs (all of the above is from reading). I did not run the other
  server (OpenUsenetServer) or an auth-required server.
- I did not check what the greenbender/inn image's certificate and CAPABILITIES
  look like beyond what the CI file and setup.sh show.
- I judged the code, not the PR text. CONTRIBUTING I checked only for
  agreement with the code's skip logic, and it agrees.

## Score

9.0. The default/CI path is intact, and no test can pass whatever the client
does. What keeps it below 9.5 are the two Low wrong verdicts in the
other-server mode that this PR adds: finding 1 hits exactly the login servers
the PR says it supports, and finding 2 hits remote INN servers. With both fixed
or explicitly documented, 9.5.

#167: 9.0, 2 findings (0/0/2): login-refused test leaves wrong credentials so date() fails on login servers; check_newsgroups demands INN stock groups on a remote INN despite PYNNTP_GROUPS
