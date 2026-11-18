The integration tests assume INN on localhost. Running them against another server (OpenUsenetServer) showed what else they assume: INN's default groups, its `junk` group, its exact empty-group reply, no login, and port 563. This makes the server and those assumptions configurable. The defaults are unchanged, so CI runs the same tests as before.

### Changed
- **Server and login:** `PYNNTP_HOST`, `PYNNTP_PORT` and `PYNNTP_TLS_PORT` (0 skips the implicit TLS tests) choose the server. `PYNNTP_USER`/`PYNNTP_PASS` are passed to every client, which logs in when the server answers 480. A `client()` helper builds every connection.
- **Groups:** `PYNNTP_GROUPS` names the groups the tests may post to (default `local.general,local.test`, the last one used by most tests). `PYNNTP_POST_WAIT` sets how long to wait for a posted article to be listed (default 10 s).
- **INN only:** the check for INN's default groups and the `junk` tests (LIST ACTIVE status `n`, posting refused with 441) run only when CAPABILITIES says `IMPLEMENTATION INN`. Other servers must list the test groups instead.
- **Empty group:** `PYNNTP_EMPTY_GROUP` names one (INN: `junk`). The test now accepts every empty-group form of RFC 3977 6.1.1.2 (high = low − 1, all zeros, high below low), not only INN's `0 1 0`.
- **Refused login:** 481 is accepted besides 483 and 502 (RFC 4643: a server with logins refuses the wrong one).
- CONTRIBUTING.md mentions the variables; the module docstring lists them all.

### Behaviour change
Tests for features a server may lack (HDR, OVER, LIST ACTIVE.TIMES, an Xref header and the like) skip only when `PYNNTP_HOST` is set, that is against another server. Without it (the default INN runs) such a gap still fails, so a client bug can't become a skip. CONTRIBUTING.md lists which tests skip when.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
