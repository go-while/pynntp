# Round 0 review: PR #171 (fix/160-xz-last-row, c84dc8d) by hk-r0-sonnet-a

Method: read the net diff `upstream/main...origin/fix/160-xz-last-row`, `_info_yenczlib`, `_xover`, `_number_values`, `utils.parse_number_value`, the new tests, PR body and issue #160. No host run; nothing here claims tests passed.

Score: 9.5 / 10. Findings: none.

## What the change does
At the end of `_info_yenczlib`, after the trailer check and the `inflate.eof` check, the bytes left in `buf` (a last row without CRLF) are yielded (3 lines, nntp.py:566-568).

## Checks (by reading)
- Order is right: nothing partial is yielded unless the trailer, size/CRC and end-of-stream checks passed (test_xzver_unterminated_row_bad_trailer).
- Consumers cope with a row without CRLF: `_xover` uses `rstrip("\r\n")`; `parse_number_value` uses `rstrip("\r\n")`; `_decode` just decodes. So no CRLF needs to be added.
- Size bound: `_lines()` raises when `len(buf) >= max_line_length`, so the leftover is below the limit.
- Empty payload leaves buf empty, nothing yielded (test_xzver_empty_compressed_stream); a payload ending in CRLF leaves nothing extra.
- Leftover that is not a row (e.g. a lone "\r" or junk at the end of a verified stream) is yielded and then raises NNTPDataError in `_xover`/`_number_values` via `_data_errors`, which marks the connection broken but the terminator is already read. A broken server only; acceptable and visible (no silent loss).
- `_info_gzip` has no equivalent gap: its rows are framed by the plain terminator, so a row without CRLF cannot be told from the terminator; not part of #160.
- Tests: the `terminated=False` rows fail on base (last row dropped), the terminated rows and the bad-trailer test pass on both (they are guards). Docstring of `_info_yenczlib` says "same lines as _info_plain() would give": still true enough (the last line lacks CRLF), could mention it.

## Notes (non-findings)
- PR body count "12 fail on main" not verified.
- Docstring nit: `_info_yenczlib` could say the last line may lack CRLF; no code impact.

## Not checked
No host run.
