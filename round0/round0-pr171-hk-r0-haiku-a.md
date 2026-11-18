# Round 0 review: PR #171 (fix/160-xz-last-row, head c84dc8d)

Reviewer: hk-r0-haiku-a (Haiku 5.5, round 0, read-only). Base: upstream/main 2bfca17.
Scope: #160, XZVER/XZHDR dropped a last row without CRLF silently.
Change: one commit, nntp/nntp.py `_info_yenczlib` end (head ~:566-568): after the trailer and the eof checks,
`if last := buf.read(): yield last`. Tests in tests/test_overview.py (test_xzver_last_row,
test_xzhdr_last_row, test_xzver_empty_compressed_stream, test_xzver_unterminated_row_bad_trailer).
Method: read head nntp/nntp.py _info_yenczlib, _lines, _xover, _number_values, and BytesFifo (nntp/fifo.py
read/readline), utils.parse_number_value; read the test diff and issue #160. No code run, no host run.

## Findings

### 1. Low: an LF-only (non-CRLF) compressed response is now merged into one bogus row, instead of being dropped

- File: nntp/nntp.py, end of `_info_yenczlib` at head (the new `yield last`), with `_lines` (head :431-438)
  checking only the length of an incomplete tail.
- Input: a broken server (violates RFC 3977 line endings) sends an XZVER/XZHDR payload with LF-only rows that is
  shorter than max_line_length in total, e.g. `1\thello\tme\n2\t.dot\tyou\n`, inside a valid yEnc/zlib block.
- What goes wrong: BytesFifo.readline() finds no CRLF, so `_lines` yields nothing and the whole payload stays in
  buf. The new `yield last` then yields the whole payload as one row. `_xover` (line 1667) does
  `rstrip("\r\n").split("\t")`, so the result is one row with article 1 and HeaderDict fields containing
  "me\n2", while article 2 is absent. Silent. On base the same input yields zero rows, also silent, so the
  silent loss existed; this PR changes the shape to a merged, wrong row.
- Confirmed by reading (BytesFifo line splitting on CRLF only; `_lines`; `_xover`). Not run.
- Severity Low: needs a server that breaks the protocol's line endings, and the base already dropped the rows
  silently. A fix would be to treat a final partial row only when it is the stream's last bytes AND contains no
  LF, or to reject LF-only payloads (NNTPDataError) in _info_yenczlib.
- New in the change (the `yield last`).

## Checked by reading (no finding)

- Ordering: the trailer check and `inflate.eof` check run before `yield last`, so a partial row is never
  returned for a bad block or a truncated stream. test_xzver_unterminated_row_bad_trailer covers that.
- `buf.read()` (fifo.py:96-110) returns all unread bytes, after `_append()`; `_lines` has already yielded every
  complete CRLF line, so the leftover is only the unterminated tail. Covered.
- The tail length is bounded: `_lines` raises NNTPDataError (nntp.py `if len(buf) >= self.max_line_length`) for an
  unterminated tail at max_line_length or more before the end, so `last` is below max_line_length. No
  memory issue added.
- Empty payload: buf is empty, nothing yielded (test_xzver_empty_compressed_stream). Covered.
- Consumers: `_xover` uses rstrip("\r\n") and `_number_values` uses utils.parse_number_value, which also
  rstrips. An unterminated last row parses the same as a terminated one. Checked by reading.
- Connection sync: the yield happens inside the response generator before its end, so `_response` still sees
  StopIteration after it and sets complete. Covered.
- Tests: test_xzver_last_row (rows 1 and 2, terminated and not) fails on base for the unterminated cases (base
  returns [] or one row less), and passes on head by reading.

## Notes (not findings)

- Docstring mismatch (minor): `_info_yenczlib` says "The lines are the same as _info_plain() would give for the
  uncompressed command". An uncompressed response always ends a row with CRLF before ".", so the new unterminated
  final row is a difference from _info_plain(). The docstring should say the final row may lack CRLF.
- The issue #160 text says "Covered as an expected failure (xfail) in #145: xzver/last-row-without-crlf". This
  PR adds the real tests instead; check that #145's xfail is removed or not left stale. Not a code defect.
- Single concern (the last row of the XZ stream). One commit.

## Did not check

- Real servers' XZVER output (no network, no host run).

## Score

8.5 / 10. The change does what #160 asks, the ordering is right, and the tests fail on base. Finding 1 is a
Low for a protocol-violating server; a docstring line would make the new behaviour explicit.
