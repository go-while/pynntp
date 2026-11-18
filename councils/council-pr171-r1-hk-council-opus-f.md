# Council r1: PR #171 (fix/160-xz-last-row, head 8ac5794), reviewer hk-council-opus-f

Base upstream/main 2bfca17. Reviewed: net diff, `_info_yenczlib`, `_lines`, `BytesFifo.readline` (splits on CRLF only),
`_xover`/`_number_values` parsing of the final row, and the new tests. By reading only; no host run.

Score: **9.5**

## Findings
None.

## Checks
| Check | Result |
|---|---|
| One concern | Yes: the final XZ row without CRLF (keep it, but don't let a bare-LF payload pass as one row). |
| Fails on base, passes on head (by reading) | `test_xz*_last_row[terminated=False]`: base leaves the row in `buf` and drops it. `test_xz*_lf_only_rows`: base returns no rows silently (the whole payload sits in `buf`); head raises. `test_xzver_empty_compressed_stream` and `test_xzver_unterminated_row_bad_trailer` pass on both and guard the order: the leftover is yielded only after the trailer, CRC and `inflate.eof` checks. |
| Edge cases | Leftover size stays bounded below max_line_length, because `_lines()` checks `len(buf)` after every write. Output pending at `_INFLATE_SIZE` is drained before `eof` is tested. An unterminated row parses the same as a terminated one (`rstrip("\r\n")` in `_xover`, `parse_number_value` for XZHDR). The response is read to its end before the bare-LF error. |
| Docstring | Matches, apart from the wording note below. |

## Notes (not findings)
- nntp.py:568 says "Rows separated by a bare LF are not one row: refuse them", and the Raises text at :534 says "the data
  ends with a bare LF". Both only describe the unterminated tail. A bare LF inside a CRLF-terminated row
  (`1\thello\tme\n2\t.dot\tyou\r\n`) is still yielded as one merged row. Base and plain XOVER do the same, so this is
  pre-existing and out of scope. Suggested wording: "A tail without CRLF that holds a bare LF is refused" and "or the data
  after the last CRLF contains a bare LF".
- A final leftover of just `\r` now gives NNTPDataError from the row parser (`int("")`). Base dropped it silently. It
  fails loudly and only on broken servers.
- Process: #171 conflicts textually with #170 in the `_info_yenczlib` docstring. Whichever merges second needs a rebase.

## Not checked
No host run. Not checked whether a real XZVER server puts the dot terminator inside the compressed data (pre-existing
either way).
