Which parts of `nntp/` have been reviewed since 3.0.0, and how; the review list from #143 as one issue instead of a REVIEW.md file. Comment here to take an area, so two people don't review the same code.

Status values: not started, partial, in progress, reviewed (date), reviewed 2× (date), reviewed 3× (date). "Fixed in" lists the merged PRs for findings in that area, "Open" the issues still open, "PRs" the open PRs for that area.

| # | Area | Code | Status | Fixed in | Open | PRs |
|---|---|---|---|---|---|---|
| 0 | Docs | `README.md`, `index.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, `docs/`, docstrings | partial: README command list and CHANGELOG claims (2026-11-09) | – | – | – |
| 1 | Connection and TLS | `BaseNNTPClient.__init__`, `_connect`, `reconnect`, `_enable_tls`, `close`; `NNTPClient.__init__`, `from_url`, `_connect`, `__enter__`, `__exit__`, `quit` | reviewed 4× (2026-11-17) | #133, #142 | – | #186, #180 |
| 2 | Commands, status and login | `status`, `command`, `_unexpected`, `_command`, `login`, `_sync`, `_MULTILINE` | reviewed 4× (2026-11-17) | #133, #141, #146, #147 | #161 | #187, #179 |
| 3 | Reading and compression | `_recv`, `_decompress`, `_send`, `_readline`, `_read`, `_info_plain`, `_info_gzip`, `_info_yenczlib`, `_info`, `_response`, `info`, `compress`, `xfeature_compress_gzip`; `fifo.py` | reviewed 4× (2026-11-17) | #134, #138, #148 | #154, #155, #160, #162 | #168, #171 |
| 4 | Articles and yEnc | `_read_body`, `_decode_yenc`, `article`, `head`, `body`; `yenc.py` | reviewed 4× (2026-11-17) | #134 | #159 | #170, #178, #183, #181, #185 |
| 5 | Session and group commands | `capabilities`, `mode_reader`, `date`, `help`, `newgroups`, `newnews`, `list*`, `group`, `listgroup`, `next`, `last`, `stat`, `_select`, `_timestamp` | reviewed 3× (2026-11-17) | #135, #138, #141, #149 | #157 | #173 |
| 6 | Overview and headers | `_overview_fields`, `overview_fmt`, `_xover`, `xover`, `xzver`, `over`, `_hdr`, `_number_values`, `hdr`, `xhdr`, `xzhdr`, `xpat` | reviewed 3× (2026-11-17) | #135 | #158 | #174 |
| 7 | POST and IHAVE | `post`, `ihave`, `_transfer`, `_prepare_article`; `utils.unparse_headers` | reviewed 3× (2026-11-17) | #135 | #156 | #169, #182 |
| 8 | Helpers | `utils.py`, `headerdict.py`, `types.py` | reviewed 3× (2026-11-17) | – | #158, #163, #164, #165 | #172, #174, #175, #176, #184 |
| 9 | Tests and CI | `tests/`, `.github/workflows/` | partial: integration tests on stock INN 2.7.2, 2.7.4 and 2.8 (#144); fault-injection scenarios (2026-11-09); fresh review of #145 and #167 (2026-11-14); all open PRs' tests and CI read with the merged code (2026-11-17) | – | – | #145, #153, #167 |

Function names refer to 3.3.0.

### Open findings
- #154 XZVER/XZHDR fail when the DEFLATE stream is complete but not finished
- #155 gzip TERMINATOR: the reply waits for the end of the gzip stream after the terminator
- #156 (PR #169) `post()` takes the first `<...>` anywhere in the 240 reply as the Message-ID
- #157 (PR #173) group() returns negative or malformed numbers from the 211 reply unchecked
- #158 (PR #174) HDR/XHDR/XPAT: any first token starting with `<` gets article number 0
- #159 (PR #170) A stray =yend after a complete yEnc block raises NNTPYEncError
- #160 (PR #171) XZVER/XZHDR drop a last row without CRLF silently
- #161 (PR #187) Data the server sent beyond a reply becomes the reply to the next command
- #162 (PR #168) An iterator resumed after reconnect() reads the new connection's lines
- #163 (PR #172) parse_headers() drops the whitespace before a folded line
- #164 (PR #175) LIST OVERVIEW.FMT: empty or space-padded field names are accepted
- #165 (PR #176) A range tuple with True/False is sent (OVER True-) instead of raising

### Findings from the 2026-11-14 review round
Not filed as separate issues; each has its own PR, or a follow-up commit in an open PR.

Fresh whole-file review of `nntp/` and of our own patches:
1. yEnc: a `=ybegin` inside an open block is not reported, so the missing `=yend` and that block's size/CRC are never checked. PR #178.
2. An empty, blank or bool message-id/article argument is dropped or sent as `True`, so `stat("")`, `body("")`, `over("")` etc. act on the current article. PR #179.
3. POST/IHAVE: an iterable body item with an inner LF is sent unstuffed with a bare LF, so a `.` line inside it can end the article early. PR #182.
4. A failed `reconnect()` (connection refused) leaves the client not marked broken; the next command fails with a raw `OSError`. PR #180.
5. `NNTPYEncError` can't be pickled or copied (its `args` lack `data`). PR #181.

Deep review (input hardening, authentication, memory, throughput, logic, threading):

6. The yEnc keyword regex is quadratic: one `=ybegin`/`=yend` line with 64 KB of word characters costs about a minute of CPU in `body()`/`article()` (65 s measured on a test host). Anyone who can post an article can trigger it. PR #183.
7. `copy.copy()` of a `HeaderDict` shares its storage with the original. PR #184.
8. `head()` leaves the rest of the response unread at a blank line or a bad header line, so the next command fails. PR #185.
9. An invalid `ssl_mode` (e.g. `"STARTTLS"` in upper case) with `use_ssl=True` connects in plain text, and the password goes in clear on a 480. PR #186.
10. `parse_headers()` unfolding is quadratic in the number of continuation lines (follow-up in #172).

Low impact, not fixed: each needs a hostile server, a deliberately crafted input, or an unusual chain of conditions:
- POST/IHAVE: a header name starting with `.` (e.g. `.X-Foo`) is not dot-stuffed, so the server reads it as `X-Foo`.
- LISTGROUP, XOVER/OVER/XZVER and ARTICLE accept `-1`, `+3`, `1_0` and non-ASCII digits as article numbers.
- `from_url()`: some error messages can contain parts of the password (unencoded `?`/`#`/`@`, full-width characters); non-UTF-8 `%XX` in the user info becomes U+FFFD.
- `"COMPRESS=GZIP"` anywhere in a status line selects gzip, also without XFEATURE; a Message-ID `<COMPRESS=GZIP@x>` makes that article unreadable and breaks the connection.
- More than 4300 digits in a yEnc `size=` or a STAT reply raise a plain `ValueError` (Python's int() limit) instead of an NNTP error; LIST ACTIVE numbers accept `-5`, `+5`, `1_0`.
- 202 (LIST EXTENSIONS) and 218 (XINDEX) are missing from the multi-line codes, so an unexpected 202 or 218 leaves its block unread.
- `login()`: a password with a lone surrogate raises `UnicodeEncodeError` whose `repr()` contains the password.
- XZVER/XZHDR keep feeding data after the end of the zlib stream to the decompressor, which buffers it at quadratic cost and then drops it silently, so a second stream is lost (malicious server).
- XZVER/XZHDR and plain XOVER/XHDR: a row ended by a bare LF followed by a CRLF row is read as one row, so the next row is lost (buggy server; only a bare LF in the last, unterminated row is refused).
- yEnc single-part: the `size=` of `=ybegin` is not compared with the decoded size; only the `=yend` size is.
- `unparse_range()` doesn't check item types: `(1, None)` is sent as `1-None` (caller error; the server rejects it).

Noted, not fixed yet:
- `unparse_msgid_range()` passes any string through, so `over("1 foo")` sends `OVER 1 foo` (CR/LF/NUL are refused).
- gzip TERMINATOR: decompressed bytes after the inner terminator are read as the next status line (malicious server; related to #155).
- XZVER/XZHDR trailer and CRC errors are raised after the terminator was read, but still mark the connection broken.
- LIST OVERVIEW.FMT: `Bytes:` and `:bytes` give the same field name; the cached format is not reset by `reconnect()`.
- Python 3.11 only: `cached_property` holds one lock for all clients while the first LIST OVERVIEW.FMT runs.
- `=ypart` lines in an XZVER/XZHDR reply would be decoded as data.
- Throughput: `recv(4096)` per read; XZVER inflates one line at a time.
- Design limits: no cap on the total size of `body()`/`article()`/`head()`; the timeout applies per read, not per response.

### How the review was done
- The go-while fork's own fixes (develop-01) were compared with 3.0.0 to 3.2.0, one probe per difference against a fake server; the results are in #102.
- #133 to #138 were reviewed after merging and run on Linux with Python 3.11 to 3.15.
- Upstream's suite with its integration tests ran against INN 2.7.2 and 2.7.4 (Ubuntu inn2) and INN 2.8 (InterNetNews/inn main, built from source); see #144.
- Fault-injection scenarios ran over real TCP, TLS and COMPRESS against the nntp-testkit fake server (split and slow writes, drops, unexpected and malformed replies): #159, #160, #161, #162.
- 2026-11-10: area 8 was read and probed (CPython 3.12), including generated `HeaderDict` operations (fixed seed) checked against a simple model: #163, #164, #165.
- 2026-11-14: every open PR got a fresh whole-file review; the findings were checked against the code and fixed in the PRs.
- 2026-11-14: all of `nntp/` (with all open PRs merged) got a fresh deep review; every finding above was checked against the code. Fixes are written test-first.
- 2026-11-15: a second round of fixes after another review of every fix; each fix's new tests were checked to fail without it. All open PRs and these fixes were run together with the unit tests, ruff, ruff format and mypy --strict.
- 2026-11-16: the new PRs were reviewed again, and only findings with a realistic trigger were kept. Findings that need a hostile server or an unusual chain of conditions are listed above as low impact, not fixed.
- 2026-11-17: all open PRs merged together on 3.3.0 (branch `integration-1` on go-while/pynntp) pass the unit tests, ruff, mypy --strict, the fault-injection scenarios and the INN integration tests. Two interactions between PRs showed up only in that combined run (#177's ruff rules and a positional bool in #174; #145's made-up `240 ok <id>` replies and #169) and were fixed in #174 and #145. A review of the combined diff and a deep review of all of `nntp/` on that branch found nothing above low impact; the new low-impact items are listed above.

### Checked, not a defect
- STARTTLS: data after the 382 in the same read raises `NNTPProtocolError`; in a later read the TLS handshake fails; 580/200 to STARTTLS fail the constructor with no plain-text fallback; no AUTHINFO is sent before TLS in any spelling of the command (checked for bypasses of the #133 guard).
- No AUTHINFO after COMPRESS, also not on a 480 (RFC 8054).
- `BytesFifo`: `len()` counts queued writes, compaction is amortized; the block yEnc decoder completes an escape split across reads.
- INN-style `Z_PARTIAL_FLUSH` COMPRESS replies decode without waiting for more data.
- LISTGROUP's unparsed 211 line: only the article numbers are returned.
- 2026-11-14: STARTTLS ordering, no credentials after COMPRESS, credential masking in errors, the line-length cap (also after decompression) and `BytesFifo` were checked again and hold. No shared module state; one client is not thread-safe, and nothing claims it is.


