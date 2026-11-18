# Council r1: PR #173 (fix/157-group-numbers, head 95dae73) — hk-council-opus-g

Base upstream/main 2bfca17. Fixes #157. Reviewed by reading only (G1); no host run, so no claim that tests pass.

## Score: 9.5 — 0 findings

## Findings
None.

## What I checked
| Check | Result |
|---|---|
| Change | nntp/nntp.py:1282-1285: group() rejects the 211 reply unless it has 4+ fields and the first three are ASCII decimal digits; raised as ValueError inside the existing try, so it surfaces as NNTPDataError 'Invalid GROUP status "..."' (docstring "If the reply can't be parsed" matches). |
| Inputs from the issue | `-5`, `+3`, `1_0` and Unicode digits (`١`, accepted by int()) are rejected; reply is decoded as UTF-8 (nntp.py:263), so the `١` case really reaches the check as one non-ASCII digit. |
| Real servers | Normal replies (`211 0 1 0 g`, `211 0 0 0 g`, leading zeros, extra trailing fields after the name) still parse; huge digit strings fail int()'s digit limit with ValueError -> NNTPDataError. |
| Sync | 211 is single-line; nothing unread after the error. The test also proves the next command (DATE) works. |
| Test fails on base / passes on head (by reading) | tests/test_commands.py:276: all 12 cases return a tuple on base (int() accepts all four tokens), so pytest.raises fails on base; on head each raises. |
| One concern | Yes, group() only. |
| Merge with the other open PRs | `git merge-tree` against #169, #171, #172, #174, #175, #176: no conflicts. |

## Notes (not findings)
- Style: nntp.py:135 already has `_DIGITS_RE = re.compile(r"[0-9]+")`, used by `_select()` for the same purpose. `_DIGITS_RE.fullmatch(part)` would say the same thing as `part.isascii() and part.isdecimal()` and keep one idiom in the module. #174 uses the isascii/isdecimal idiom too, so whichever is chosen should be the same in both.
- `len(parts) < 4` repeats what the IndexError branch already caught; harmless, makes the intent explicit.
- Out of scope, pre-existing: no check that first <= last + 1 or that count fits the range (RFC 3977 says the count is an estimate). LISTGROUP lines (nntp.py:1329) already reject numbers below 1 but go through int() too, so `+5`/`1_0` there are accepted; worth a line in #166 if not already there.

## Not checked
- No host run (ruff, mypy, pytest). The lead reports base-fail/head-pass and the full check.
- Other servers' real GROUP replies beyond INN behaviour I know.
