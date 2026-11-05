# pynntp code review (October 2026)

> Made by AI (Claude, via Claude Code) for go-while, who plans to maintain this fork. The bugs marked
> "reproduced" were run against INN (current main, built from source), against the `greenbender/inn`
> image (INN 2.7.2), or against the small scripted server in `review/probes/fake_server.py`. The rest
> come from reading the code. Line numbers refer to upstream `main` at 82b9b2b.

## Status on develop-01 (2026-11-05)

Fixed on the fork's `develop-01` branch, each with offline regression tests against a scripted server and,
where possible, tests against INN 2.6.4 and 2.7.4. Every change was reviewed and verified by two other agents
before it was merged. The merge commits are in `git log --first-parent develop-01`.

| Item | Status | Merge |
|---|---|---|
| Bug 1: dot-unstuffing (#99), plus gzip replies read to their end | fixed | 56f765e |
| Bug 2: LIST ACTIVE / NEWGROUPS high and low | fixed | 387c249 |
| Bug 3: NEWGROUPS / NEWNEWS send `GMT` | fixed | e0e48f6 |
| Bug 4: HDR expects 225; unexpected multi-line codes drained | fixed | c4c81ef |
| Bug 5: abandoned or failed replies lock the client | fixed | 1b5c877 |
| Bug 6: `close()` / `quit()` / `__exit__` | fixed | 64acff4 |
| Bug 7: MODE READER before STARTTLS, buffer cleared, no AUTHINFO before TLS | fixed (CAPABILITIES re-read deferred) | 53f273d |
| Bug 8: CR/LF injection in headers | fixed | 7f1ea38 |
| Bug 8: CR/LF injection in command arguments | open (B5) | |
| Bugs 9, 10: POST truncation, Message-ID from 240 | fixed | ee9af71 |
| Bug 11: AUTHINFO | in review (B4) | |
| Bug 12: XHDR values and message-id form | fixed | 3fd109e |
| Bug 13: socket leaks on failed setup | fixed | c08d9b0 |
| Low: yEnc size/CRC check, text after `=yend` | fixed | b4b2208, 9ab7270 |
| Low: `ValueError` from parsers | fixed | 9ab7270, 3c14d66 |
| Low: `:full` overview fields keep their label | fixed | 3c14d66 |
| Low: LIST EXTENSIONS 202 vs 501 | documented (obsolete; use CAPABILITIES) | 3c14d66 |
| Missing: STAT, LISTGROUP, OVER (#43, #45, #46) | added | 9799bbf |
| Tests: offline scripted-server tests, integration tests opt-in, ARTICLE test independent of numbering | done | 6a4fa47, 7926aa2, d40752c |
| Packaging: PEP 621, Python >= 3.10, `py.typed`, tests in the sdist (#74), refreshed lock | done | 347c2a1, 2387beb |
| CI: lint + Python 3.10-3.14 against Ubuntu's inn2 on every work branch | done | 9947800 |
| README example and command list | fixed | f1a67ba |

Still open: B5 (command arguments), B6 (TLS options, timeouts as `NNTPError`, exports), C9 (unexpected codes
everywhere), the `__main__` demo block, the publish workflow, COMPRESS DEFLATE (#41), IHAVE (#42).

## Summary

pynntp is small: one 1.4k-line `nntp/nntp.py` plus helpers, typed and readable. The protocol layer has
serious bugs, though:

- dot-unstuffing has been wrong since 2013;
- `newgroups()` and `newnews()` have been broken against INN since 2.0.0;
- `hdr()` has never worked against an RFC 3977 server.

The CI doesn't catch any of this, because only about half of the client code runs in tests, and some
integration assertions check nothing or assert the buggy values. The tooling is fine; packaging and
release need work. Everything is fixable in a few days, with no rewrite needed.

The integration suite passes against both servers (40 passed, 14 xfailed). It also passes when run a
second time against the same server, which is itself a sign of the test problems below.

## Bugs (file:line in `nntp/nntp.py` unless noted)

### High

1. **Dot-unstuffing yields every dot-stuffed line twice**, once unstuffed and once raw, because there
   is no `else`/`continue` (`:303-305`, and the same in the gzip path `:353-355`).
   - Effect: corrupts BODY, ARTICLE, HEAD, LIST and XZVER output.
   - Reproduced: post a body with a line starting with `.` and read it back with `body()`.
   - It is the root cause of **#99**: a yEnc body with one encoded line starting with `.` decodes to
     1152 bytes instead of 1024.
2. **LIST ACTIVE / NEWGROUPS put high and low the wrong way round** (`utils.py:102-110`). RFC 3977
   sends "group high low status".
   - Reproduced: the server sends `local.test 0000000002 0000000001 y`, and pynntp returns low=2,
     high=1.
   - `test_inn2.py` asserts the swapped values for junk.
3. **NEWGROUPS and NEWNEWS send `UTC`** (`:720`, `:755`, from `%Z` with `timezone.utc`). RFC 3977
   only allows `GMT`, so INN answers `501 Syntax error` and both functions always fail against INN.
   - This is a regression in 2.0.0; 1.0.4 sent `GMT`.
   - Reproduced on both servers.
4. **`hdr()` expects code 221, but RFC 3977 HDR returns 225** (`:1165`).
   - It always raises, and because the multi-line answer is left unread, every later command on that
     connection reads stale data. Reproduced: one failing `hdr()` cascaded into wrong results for about
     15 later commands.
   - The same desync follows whenever a multi-line command gets a success code it didn't expect,
     because nothing drains the block (the pattern is at `:617`, `:793`, `:1165`, `:1259`).
5. **An abandoned or failed generator locks the client up permanently** (`:298-307`, `:335-357`).
   `_generating` is only reset after a normal end, never in a `finally`.
   - Reproduced: after `for g in c.list_active(): break`, `next(c.capabilities())` or a parse error,
     every later command raises `NNTPSyncError`.
   - Inside `with`, `__exit__` (`:587-591`) then raises `NNTPSyncError`. A plain `break` in a `with`
     block makes the block raise, and a user's own exception gets masked by it.
6. **`close()` and `quit()` are not idempotent** (`:499-505`, `:639-656`, `__exit__` `:580-592`).
   - Calling `quit()` or `close()` inside `with` gives `OSError [Errno 9]`; so does a second `quit()`.
   - `__exit__` only catches `NNTPError`, so `OSError` and timeouts escape and leave the socket open.
   - The two strict xfails in `test_inn2.py` hide this bug.

### Medium

7. **STARTTLS** (`:169-174`, `:573`):
   - `MODE READER` is sent *after* TLS. RFC 4642 section 6 says "the MODE READER command MUST NOT be
     used in the same session following a successful TLS negotiation". In practice the client can't do
     STARTTLS with innd (only nnrpd), which is why a test setup must not make localhost a feeding peer.
   - `_buffer` is not cleared after the 382 reply, so plaintext injected after it would be read as if
     it came over TLS (STARTTLS response injection). From reading only.
   - CAPABILITIES are never read, so nothing is re-read after TLS or authentication.
8. **CR/LF injection.**
   - Header values with CRLF are not checked (`utils.py:178-190`). Reproduced: an extra
     `X-Injected: yes` header appeared in the posted article.
   - Command arguments are not checked either (`:481`). Reproduced on the fake server:
     `GROUP a\r\nPOST` was sent as two commands.
9. **`post()` posts a truncated article** when the body contains NUL or a bare CR, and only raises
   afterwards (`:1415-1434`). Reproduced: the article was stored with just "ok line".
10. **`post()` returns `True` instead of the Message-ID on INN** (`:1441-1445`). It only looks at the
    first word, and INN answers `240 Article received <id>`.
11. **AUTHINFO** (`:485-495`):
    - If the server keeps answering 480 after 281, the client recurses until `RecursionError`
      (reproduced: 2974 commands sent).
    - With no username it sends a bare `AUTHINFO USER` (reproduced, 501).
    - A 480 on MODE READER leads to MODE READER being sent again after authentication, which
      RFC 4643 forbids (from reading).
    - 483 (encryption required) is not handled, and there is no explicit `login()`.
12. **XHDR** (`:1170-1176`):
    - Values keep their trailing `\r\n` (reproduced).
    - The message-id form `XHDR Subject <id>` fails with `NNTPDataError` and then locks up the client
      (reproduced).
13. **Socket leaks** when the greeting fails, STARTTLS answers 580, or MODE READER fails
    (`:165-174`, `:573`). Reproduced as `ResourceWarning`.

### Low

- Overview fields marked `:full` keep their "Xref: " prefix (`:1264-1267`): `'Xref': 'Xref: host local.test:1'`.
- `PYNNTP_TLS_INSECURE=0` also turns certificate checking off (`:178`; reproduced). Certificates are
  checked by default, but there is no way to pass an `ssl_context`.
- Timeouts come out as a bare `TimeoutError`, which is not an `NNTPError`, contrary to the docstring
  at `:189`.
- `ValueError` escapes from `parse_newsgroup`, `parse_headers` and `parse_date`.
- `NNTPSyncError` is not exported (`:44-53`).
- `NNTPProtocolError` is built from bytes (`:264`).
- LIST EXTENSIONS expects 202, from an old draft; INN answers 501.
- yEnc in `_body` doesn't check the CRC or size, and text after `=yend` gets decoded too (`:1012-1034`).
- Repeated headers: the last one wins. RFC 2047 encoded words are not decoded.
- Generator methods (capabilities, newgroups, list_active, xover…) only send their command on the
  first `next()`.
- The library contains a 300-line `__main__` demo (`:1448-1757`) that posts to `misc.test` and calls
  `xhdr` where it means XZHDR.
- Stale docstrings ("_gen versions", "hdr_gen()", "XZVER … compressed version of XHDR").
- Missing commands: STAT, LISTGROUP, OVER, IHAVE, COMPRESS DEFLATE (RFC 8054, #41), AUTHINFO SASL.

## Tests

- **What's covered:** unit tests for utils, headerdict and the yEnc decoder only.
- **Coverage:** 44% overall, measured with the integration tests against `greenbender/inn`.
  `nntp.py` is 32%, or about 50% without the demo block.
- **Never run:** dot-stuffing, gzip, XZVER, auth, NEWGROUPS/NEWNEWS, HDR/XHDR/XOVER/XPAT, HEAD/BODY,
  NEXT/LAST, DATE, CAPABILITIES, and every error path.
- **Assertions that check nothing:** `assert low == 0 if newsgroup == "junk" else 1` parses as
  `(low == 0) if … else 1` (`test_inn2.py:120,122,139,141`).
- **Swap passes on re-runs:** `high == 1` keeps passing after several posts only because high and low
  are swapped (bug 2).
- **Order and freshness:** `test_article` depends on `test_post` running first, and on article 1
  existing on a fresh server.
- **xfails:**
  - The junk and utils xfails are expected errors and should be `pytest.raises`.
  - The two context-manager xfails hide bug 6.
- **Offline use:** the integration tests can't be skipped without a server, and the tests are not in
  the sdist (#74).

### The LIST NEWSGROUPS test

`test_inn2.py` compares LIST NEWSGROUPS, names *and* descriptions, with a fixed set:
`control`, `control.cancel`, `control.checkgroups`, `control.newgroup`, `control.rmgroup`, `junk`,
`local.general` and `local.test`, with descriptions that have no final period.

- **Where it comes from.** The tests were written in September 2024 against Ubuntu's
  `apt-get install inn2`, then switched to the `greenbender/inn` image. Both have exactly that file:
  Ubuntu 24.04's `inn2` 2.7.2 ships `/var/lib/news/newsgroups` with those eight groups and
  descriptions, with `local.general` and `local.test` postable. The image copies the same file.
- **Upstream INN differs.** Its `samples/newsgroups.minimal` has the same six control and junk groups,
  but with a final period, and has no `local.*` groups at all. Against a default upstream INN, 7 tests
  fail on the descriptions alone.
- **How nnrpd answers.** nnrpd answers LIST NEWSGROUPS straight from that file. A group created with
  `ctlinnd newgroup` but without a description is not listed. That is #95: INN behaviour, not a
  pynntp bug, and RFC 3977 section 7.6.6 lets the list be incomplete.

**Recommendation.** Don't expect upstream INN's text (it breaks against Debian and Ubuntu), and don't
ignore the period. Both still tie the test to one server's data file. Instead:

- **Environment contract:** integration tests skip unless `PYNNTP_TEST_HOST` is set. Ports and the
  TLS port come from environment variables. The posting groups default to `local.general` and
  `local.test` and can be overridden.
- **Setup script:** ship one, for example `tests/integration/inn2/setup.sh`. It creates the groups
  (`ctlinnd newgroup … y`) and appends their descriptions to `db/newsgroups`. Choose descriptions that
  exercise parsing: a final period, internal double spaces, one UTF-8 description.
- **What LIST NEWSGROUPS tests assert:** the exact name and description only for the groups the setup
  created; for other lines, only that they parse.
- **Posting tests:** use a unique Message-ID or subject token and fetch by message-id. Don't assume
  article numbers, high/low values or a fresh server, so reruns and matrix jobs work.
- **junk:** use `pytest.raises`, or skip if the server has no junk group.
- **CI servers:** run the same setup against INN built from source and against one packaged INN,
  such as Debian stable's `inn2`. Use `greenbender/inn` (unmaintained since 2024, INN 2.7.2) only as
  an extra target while it still works, not as the only one.

Until then, a stopgap: compare the set of names, or check that `{"local.general", "local.test"}` is a
subset of them (branch `compare-group-names` on this fork).

## Packaging and tooling

- **Python versions:** `python = ">=3.9"`, but 3.9 is end-of-life. Move to ≥3.10 and set ruff's
  `target-version` to match.
- **Metadata:** it uses Poetry-only `[tool.poetry]` metadata. Move to PEP 621 `[project]`, add project
  URLs (there are none) and Python version classifiers.
- **Types:** there is no `py.typed`, so the strict typing is invisible to users.
- **Dev dependencies:** ruff is capped at `<0.10`, and `pytest-benchmark` is unused.
- **Lint and type checks:**
  - `mypy --strict nntp tests` is clean.
  - `mypy --strict .` needs `sphinx_pyproject`.
  - Current ruff reports 2 issues: PYI061 at `nntp.py:838`, and PLW1641 at `headerdict.py:36`
    (`__eq__` without `__hash__`).
- **CI:** it only runs against `greenbender/inn`, and there is no build or sdist check.
- **Publish workflow:**
  - Nothing requires the tests to pass before publishing.
  - It sets the version from the tag and then opens a PR to commit it back, which needs
    `pull-requests: write`; that permission isn't granted. Not verified whether this fails.
  - The testpypi environment URL points at pypi.org.
- **Docs:** autoapi pages built from docstrings only. The README example is wrong (port 443 with
  `use_ssl`, `_tzgmt`), and POST is listed twice.

## Open PRs and issues

| # | What | Suggested action |
|---|---|---|
| PR 100 | CI on 3.10–3.15 and 3.14t, actions v6 | Merge after rework: also set `requires-python>=3.10` and ruff py310; drop the 3.15 mypy skip |
| PR 98 | pre-commit.ci quarterly | Merge |
| PR 90 | pre-commit autoupdate (ruff 0.16) | Rework: fix the 2 ruff findings, then merge |
| PR 97, 89 | dependabot lock bumps | Close; regenerate the lock instead (97 can't apply with the ruff cap) |
| PR 92 | jinja2 3.1.6 (security, docs only) | Merge, or close once the lock is regenerated |
| PR 96 (closed) | test for new groups | Leave closed: INN behaviour, and the test asserts `my.public` after creating `my.newsgroup` |
| #99 | multipart yEnc corrupt | Real bug, root cause is bug 1. Fix it and add CRC checking; sabctools could be an optional extra |
| #95 | new groups missing from LIST NEWSGROUPS | Close as not a pynntp bug (see above); document it |
| #93 | nntplib shim | Close as won't-fix; point to python-deadlib's `standard-nntplib` |
| #82 | docs | Keep open; fix the README and add examples |
| #56 | `pynntp[tests]` | Rework: ship tests in the sdist (#74), make integration tests configurable by environment variables |
| #43 | HDR/OVER | HDR is bug 4; add OVER. In the first release |
| #45, #46 | LISTGROUP, STAT | In the first release (small) |
| #42, #41 | IHAVE, COMPRESS DEFLATE (RFC 8054) | Next release |

## Roadmap for the first release of a maintained fork

1. Settle the PyPI name or ownership. The last release was 2.0.1 on 2024-09-29, so the PyPI name
   policy (PEP 541) applies if the owner can't be reached.
2. Fix bugs 1–6, then 7 (MODE READER before STARTTLS, flush the buffer, re-read CAPABILITIES),
   8–13, and the error-class cleanup. Give each fix an offline test against a scripted server.
   - Version: 2.1.0 or 3.0.0. Either way, the changelog must call out the LIST ACTIVE field order
     fix, because users who worked around the swap will see different values.
3. Rework the tests as above: scripted-server unit tests; integration tests that can be skipped and
   are configured by environment variables; no checks that pass vacuously; xfails removed; tests in
   the sdist.
4. Packaging: Python ≥3.10, PEP 621 metadata, `py.typed`, current ruff, a regenerated lock,
   publishing gated on tests, simpler versioning, README fixed, demo block removed.
5. Add STAT, LISTGROUP and OVER (HDR is fixed in step 2).
6. Next release: IHAVE, COMPRESS DEFLATE (RFC 8054), explicit `login()` and AUTHINFO SASL,
   `ssl_context`, yEnc CRC checking, sending commands eagerly.

## Not verified

- XZVER, XZHDR and XFEATURE COMPRESS GZIP against a real provider: INN implements none of them, so
  gzip was only tested against the scripted server.
- AUTHINFO against a real INN that requires authentication (scripted server only).
- The STARTTLS response injection (from reading only).
- Python 3.9–3.14. The INN host had 3.15; the scripted-server probes ran on 3.13.
- Whether the publish workflow's PR step actually fails.

## Probes

`review/probes/` holds the scripts used for the reproductions. Each takes the path of a pynntp
checkout as its argument.

- `probe_inn.py`, `probe_inn2.py`, `probe_inn3.py` talk to an INN on `localhost:119` (and 563 for
  TLS). They **post test articles to `local.test`**, so only run them against a disposable server.
- `fake_server.py` starts small scripted servers on 127.0.0.1 and needs no INN.
