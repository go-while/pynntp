# Council r2: fix/ssl-context-plaintext (PR 9), hk-council-opus-c

Reviewed: delta `git diff c63cc59..d0a1e04` and the whole PR `git diff upstream/main...d0a1e04`
(head d0a1e04 = fix/ssl-context-plaintext; one commit on top of c63cc59), with
`BaseNNTPClient.__init__`, `_connect`, `_enable_tls`, `from_url` and `types.SSLMode` at
d0a1e04 for context.
Score: **9/10**. Findings: 0 (H0/M0/L0).

## Open findings from r1

| Finding | Status |
|---|---|
| Med: from_url() refused ssl_context with an nntp:// URL | **Fixed.** The check in from_url() is gone (whole-PR diff no longer touches the body of from_url); the docstring now says an ssl_context only takes effect with a TLS scheme. The test that asserted the refusal is removed; the INN test `test_from_url` passes `tls_context()` for every URL again (test_inn2.py is back to upstream: no diff in the whole PR). |
| Low: use_ssl=False plus ssl_context or ssl_mode=STARTTLS raised | **Fixed.** Both `raise ValueError(... needs use_ssl=True)` are removed from `BaseNNTPClient.__init__` (nntp/nntp.py:301 keeps only `ssl_mode = SSLMode(ssl_mode)`), docstrings (288-298, 826-838) and README (49-52) say the settings are ignored without use_ssl=True; the two refusal tests are removed. |

## Whole PR as it stands

- nntp/nntp.py:301 `SSLMode(ssl_mode)` turns "implicit"/"starttls" into the enum and raises
  ValueError for anything else ("STARTTLS", "tls", "", None, 1) before `socket.create_connection`.
  Before the PR such a value with use_ssl=True matched neither branch in `_connect`
  (325, 332) and connected in plain text, login included; that silent fallback is the bug
  the PR fixes, and it is fixed for all values, not only the tested ones, since the
  comparison now always sees a real SSLMode.
- The port default (305) is computed after the conversion, so `ssl_mode="implicit"` gets 563
  (test_default_port covers the string values).
- `reconnect()` reuses the stored, already converted `_ssl_mode`.
- New test `test_tls_url_uses_ssl_context` checks the context reaches `wrap_socket` for
  nntps, snews and nntp+starttls URLs.

## New bugs from the delta

None. The delta only removes checks, tests and text; no import becomes unused (`ssl`
is still used in tests/test_connection.py and tests/test_from_url.py; ruff is clean).

## Notes (not findings)

- An explicit `ssl_mode=None` (with or without use_ssl) now raises ValueError. With
  use_ssl=True it used to connect in plain text, so the break is intended; with
  use_ssl=False it was harmless before and is now an error. Callers passing `None` to
  mean "default" would notice at once (no silent harm).
- No CHANGELOG entry for the new ValueError; the lead may want one under the next
  release's "Changed" or "Security".

## Host verification

Host 118 (job 146), `git archive` copy of d0a1e04: `pytest -q --ignore=tests/integration`
1049 passed; `ruff check`, `ruff format --check`, `mypy nntp tests` clean.

## Not checked

No INN integration run (test_inn2.py is unchanged against upstream in this PR); no real TLS
handshake beyond the unit tests' patched `wrap_socket`.
