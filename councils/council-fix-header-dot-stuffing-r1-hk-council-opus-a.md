# fix/header-dot-stuffing (77e70a6) — hk-council-opus-a
Score: 8

| Sev | file:line | function | what goes wrong | trigger | who |
|---|---|---|---|---|---|
| L | nntp/nntp.py:~1929 | _prepare_article | Header lines now pass the CR/NUL check, but the error text still says 'Body line', so a header CR/NUL error is mislabelled. In practice unparse_headers already rejects CR/NUL, so a caller can only reach this through a header encoding that yields such bytes. | header value that encodes to CR/NUL | caller mistake (rare) |

Splitting each item at LF changes behaviour for iterables whose items contain a bare LF mid-item: the old code sent a raw LF, which is the bug being fixed. The new behaviour is documented. Not verified on a host.
