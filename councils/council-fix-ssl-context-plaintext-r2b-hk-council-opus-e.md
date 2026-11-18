# Council r2b: PR 9 fix/ssl-context-plaintext @ 9a3379d (reviewer hk-council-opus-e, Claude Opus 5.5)

Base upstream/main 2bfca17. Reviewed by reading only (diff of the 5 commits as a whole, `SSLMode`
in nntp/types.py, both `__init__`s, `_connect`, `from_url`, README). No host run; I claim no test
results.

## Findings

Nothing found.

## What I checked

- The bug on the base: `SSLMode` is a `StrEnum`, so "implicit"/"starttls" already worked, but any
  other value ("STARTTLS", "tls") matched neither `== SSLMode.IMPLICIT` nor `== SSLMode.STARTTLS`
  in `_connect`, so `use_ssl=True` connected in plain text, and the port defaulted to 119. A caller
  mistake that failed silently with harm (credentials in clear text): a real finding, now fixed.
- Head: `ssl_mode = SSLMode(ssl_mode)` runs first in `BaseNNTPClient.__init__`, before the port,
  `self._ssl_mode` and the socket; `NNTPClient.__init__` only stores `_reader` before calling it;
  `reconnect()` reuses the converted value; `from_url` passes SSLMode members. `SSLMode(None)`,
  `SSLMode(1)`, `SSLMode("")`, `SSLMode("STARTTLS")` all raise ValueError "... is not a valid
  SSLMode", which the test matches, and the test proves no socket is opened.
- `use_ssl=False` with any ssl_mode stays plain text, as documented and tested.
- The from_url test proves `ssl_context` reaches `wrap_socket` for nntps, snews and
  nntp+starttls (one octet per read, so the STARTTLS buffer check is exercised too).
- README and both docstrings agree with the code.

## Notes (not findings)

- The docstrings say ssl_mode may be "an SSLMode or its value", but the annotation is `SSLMode`,
  so a mypy-strict caller passing "starttls" gets a type error. Either widen it to
  `SSLMode | str` or drop "or its value" from the docstring. Docs/typing only.
- `ssl_context=` without `use_ssl=True` still connects in plain text. The branch first refused it
  (f699097) and was then narrowed on purpose (d0a1e04); it is now documented ("Ignored without
  use_ssl=True"), so I treat it as decided, not as a finding.
- A case-insensitive `SSLMode._missing_` would accept "STARTTLS"; raising is also fine.

## Not checked

- No host run; real TLS handshakes (tests patch `wrap_socket`).

Score: 9.5
