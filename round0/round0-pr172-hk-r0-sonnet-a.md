# Round 0 review: PR #172 (fix/163-header-unfold, 1c083aa) by hk-r0-sonnet-a

Method: read the net diff `upstream/main...origin/fix/163-header-unfold` (3 commits), `parse_headers`, `HeaderDict`, the callers (`article()`, `head()`), the unparse round-trip tests, the PR body and issue #163. No host run; nothing here claims tests passed.

Score: 9 / 10. Findings: 1 Low (test timing), PR text stale.

## What the change does
- Folded header values keep the whitespace before the break (RFC 5322 2.2.3): lines are only stripped of CR/LF while collecting, the whole value is stripped once at the end.
- Pieces are collected in a list and joined once, so a header with many continuation lines is linear (base was quadratic: `value + line`).

## Findings

### F1 (Low, new in the change): wall-clock assertion in a unit test
tests/test_utils.py `test_parse_headers_many_continuation_lines` asserts `elapsed < 3.0` s for 500,000 continuation lines. The new code needs well under a second on CPython, so there is margin, but a timing assertion can still fail on a loaded or slow CI runner (PyPy-less, but e.g. coverage tracing, Windows/macOS shared runners). The test also allocates a 500k-element list and a ~1 MB string. Alternative that cannot flake: count work instead (e.g. 50k lines and a bound of 10x the 5k-line time, or assert on a counting `str` subclass) or keep it and accept the risk. Verified by reading; not run.

## Checks (by reading)
- `HeaderDict(generator of pairs)` is fine: constructor calls `MutableMapping.update`, which accepts any iterable of pairs; duplicates still resolve to the last value.
- First-line continuation still raises ValueError; blank line (CRLF, LF, or bare CR after `rstrip("\r\n")`) still ends the headers and leaves the rest of the iterator unread (test_parse_headers_stops_at_blank_line unchanged).
- A whitespace-only line is still a continuation (not a terminator), as on base.
- Leading whitespace of the first piece and trailing whitespace of the last piece are stripped by the single `.strip()`; internal fold whitespace stays. unparse round-trip tests still hold ("one\r\n two" -> "one two"; "one\r\n\ttwo\r\n three" -> "one\ttwo three").
- Error message for an invalid line now shows the line without its CRLF (previously with it); only the `match="Invalid header line"` test depends on it.
- Callers: `article()` and `head()` feed CRLF lines from `_decode`; `\r\n` is stripped; same result for every header without a fold. Hostile server: a header with a huge number of tiny continuation lines no longer costs quadratic time (a Low DoS before).
- Docstring of `parse_headers` matches.

## Notes (non-findings)
- PR body on GitHub covers only the whitespace fix; it does not mention the linear-time rewrite (commits 72ad63b, 1c083aa) and its "15 fail on main" and "1053 tests" are stale. Add a bullet.
- Test comment "The client passes lines without their line endings" is wrong: the client's lines keep CRLF; the test passes lines without it (both forms work).
- Visible effect for callers: Subject-like values that were folded after a trailing space now contain two spaces ("one  two"); RFC-correct, the issue accepted it as intended.

## Not checked
No host run (speed, ruff, mypy). Did not measure the 500k-line timing.
