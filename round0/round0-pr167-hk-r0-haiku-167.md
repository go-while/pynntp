# Round 0 review, PR #167 (hk-r0-haiku-167)

Head 54cb6e0 (port integration tests: configurable server, login, groups), base 2bfca17 (pynntp 3.3.0). Read-only review by reading the patch, the clean checkout and nntp/nntp.py. Nothing was run (G1: no tests, no builds, no Python on this machine), so no claim here says tests passed or failed.

## Findings

| # | Sev | New? | Where (head) | What goes wrong, and when | Confirmed by |
|---|-----|------|--------------|---------------------------|--------------|
| 1 | Low | new | tests/integration/inn2/test_inn2.py:402-409 (test_article_in_empty_group) | On the default INN CI run (no PYNNTP_* set) the test used to assert the exact INN reply `(0, 1, 0, "junk")`. Now it asserts `high < low or (low, high) == (0, 0)` for any empty form. A client or server change that returns another empty form for junk passes unnoticed. The PR text says the defaults are unchanged; this part is not. Only a wrong reply that is an empty form (e.g. low = high = 0 for a non-empty group would still fail via total) can slip through, so the impact is small. | Reading the diff and the file |
| 2 | Low | new | tests/integration/inn2/test_inn2.py:438 and :442 (test_newnews) | On the default INN run the NEWNEWS wildmat was `"local.*"`, which matched local.general and local.test. Now it is `GROUP` (local.test only), so the wildcard form of NEWNEWS is no longer exercised by the default run. The client sends the pattern verbatim, so little client code is left untested; the wildcard matching itself is INN's. Still a default-path narrowing that the PR text does not mention. | Reading the diff and the file |

Fix for both, keeping the other-server behaviour: on the default path (not OTHER_SERVER) keep the exact INN checks (`(0, 1, 0)` for junk; `"local.*"` for NEWNEWS), and use the relaxed RFC form and GROUP only when PYNNTP_HOST is set. Or state the narrowing in the PR text.

## Notes (not findings)

- compress() (test_inn2.py:267-279): if CAPABILITIES itself gets a 480 on another server, the library has already logged in during capabilities(), and the helper's login() runs a second time. RFC 4643 probably allows CAPABILITIES without auth, so this is a guess, not confirmed.
- test_tls_verifies_certificate_by_default (:312-339): on another server whose certificate the default trust store accepts, the test skips, so pynntp's default verification is not checked at all there. A positive check (the default context connects) would cover that case. Documented in CONTRIBUTING, so it is a wish.
- Module docstring (lines 1-10) says the INN checks "run only against INN". Without PYNNTP_HOST they run against any localhost server and fail if it is not INN. CONTRIBUTING describes this correctly.
- IPv6 literal in PYNNTP_HOST (for example ::1): from_url() is given `nntp://::1:119`, which urllib splits wrongly, so the four from_url tests error (loudly, not silently). Read from urllib's behaviour, not run. Fix: bracket the host when it contains ':'.
- Passwords are sent in clear text on PYNNTP_PORT (119) if that server asks for a login there. This is the library's documented behaviour; CONTRIBUTING does not warn about it. Checked for credential leaks into output: the library's AUTHINFO error messages are redacted (nntp.py `_command`), login() messages carry no value, and no __repr__ exposes the password. No leak found.
- test_xhdr (:460-478) posts an article before it may skip on another server. Harmless.
- Other-server behaviour (require, require_listed, skip_or_fail, number_in_group's Xref path, is_inn/inn_version, the 500 on CAPABILITIES) matches the CONTRIBUTING lists as far as read.

## Verified by reading (no run)

- Default port mapping: client() gives 563 for implicit TLS and 119 otherwise, the same as the constructor's default (nntp.py `__init__`), so the default connections are unchanged.
- from_url() takes username and password as options (nntp.py `from_url`), so the new kwargs are accepted.
- group() returns (count, first, last, name), so the unpacking in test_article_in_empty_group is right.
- head() returns a case-insensitive HeaderDict, so `"Xref" in headers` matches the header regardless of case.
- No CI env var sets PYNNTP_HOST (.github/workflows/check.yml:56-58 sets only PYNNTP_TLS_CAFILE), so the INN CI job runs with OTHER_SERVER False.
- test_list_active, test_post_to_junk_is_refused, test_xover_full_field, test_compress and test_compressed_article: default-path behaviour is the same as before, apart from findings 1 and 2.

## Did not check

- No run of any kind (G1). The "fails on base, passes on head" check and the INN CI run are the lead's job on a test host.
- No live server behaviour: OpenUsenetServer's CAPABILITIES, its certificate, its groups; INN itself.
- No RFC text beyond what the code comments cite (no web).
- Other review reports were not read, as instructed.

## Score

**Score: 9 for head 54cb6e0.** Below 9.5 because of findings 1 and 2: the default INN run is slightly weaker than the PR text says. Fixing both as described above should bring it to 9.5 or more. The notes are wishes, not blockers.

#167: 9, 2 findings (H/M/L): 0/0/2 - empty-group check relaxed on the default INN run; NEWNEWS wildcard narrowed on the default run
