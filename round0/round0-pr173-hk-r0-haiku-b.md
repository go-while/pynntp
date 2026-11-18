# Round 0 review: PR #173 (fix/157-group-numbers)

Reviewer: hk-r0-haiku-b (round 0, read-only). Head 95dae73, base upstream/main 2bfca17.
Scope: the net diff (nntp/nntp.py +4, tests/test_commands.py +14) and the head group().
Method: reading only. No builds, tests or host runs (G1). "Fails on base" is by reading.

One concern: GROUP 211 numeric fields must be ASCII decimal digits.

## Findings

None.

## Test by reading

- test_group_rejects_non_ascii_numbers_and_stays_in_sync (12 cases: -5, +3, 1_0, U+0661 in each of the three numeric positions). Base int() accepts all of them and returns a tuple, so pytest.raises fails on base. On head the isascii()/isdecimal() guard raises, wrapped as NNTPDataError 'Invalid GROUP status ...', which matches "Invalid GROUP". U+0661 reaches int() as a character only because nntp.py sets encoding = "utf-8". The 211 line is the only line read, and the following date() call reads the next reply, so the sync check holds.

## Checked

- isascii() and isdecimal() together accept exactly ASCII 0-9. Sign characters, underscores, Unicode digits and surrogateescape bytes are rejected.
- len(parts) < 4 raises the same NNTPDataError that base gave for the IndexError.
- A very long digit string still ends in NNTPDataError: the int() ValueError (4300-digit limit) is inside the try.
- The group() docstring matches the code: NNTPReplyError for a non-211 reply, NNTPDataError for an unparseable reply.

## Notes (not findings)

- Cross-PR, for the lead: open PR #145 (go-while/port/fault-tests, tests/faults/scenarios.py, scenario "malformed/group-negative-numbers") marks this case known="group() accepts negative numbers" with strict xfail (test_faults.py:29-30, strict defaults to True). When #173 lands, that scenario XPASSes and the strict xfail fails. The known= marker must be removed in the same change that merges #173. The scenario expects Err(NNTPDataError, state="sync"), which the head meets by reading.
- Issue #157 lists `211 -5 -3 -9 g`, `+3` and `1_0`. All are covered.
- listgroup()'s 211 parsing is separate code and is not changed by this PR.

## Not checked

- No test, ruff or mypy run (G1 and the task's read-only scope). No host run.
- listgroup() 211 handling beyond the docstring.

## Score

9 (ready as is, apart from the #145 xfail coordination note).
