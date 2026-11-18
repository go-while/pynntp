# Round 0, PR #173 (fix/157-group-numbers, head 95dae73), reviewer hk-r0-sonnet-b

Score: 9/10. Findings: none.

## What I checked
- Net diff vs upstream/main 2bfca17: nntp/nntp.py group() (+4 lines), tests/test_commands.py (+14). One concern, matches issue #157.
- nntp/nntp.py:1279-1292 at the head: the new guard requires >= 4 parts and the first three to be ASCII decimal (`isascii() and isdecimal()`), so -5, +3, 1_0 and non-ASCII digits (U+0661) raise ValueError, which is caught and re-raised as NNTPDataError('Invalid GROUP status ...'). Short replies were already rejected through IndexError; now also by the explicit length check (guard short-circuits, no IndexError path left uncovered). Huge digit strings: int() ValueError (4300-digit limit) is also caught.
- Sync: GROUP is a single-line reply, so raising after command() leaves the connection in sync. The test asserts this with a following DATE.
- Test host 116 (uv, pytest --ignore=tests/integration), head copy: 1070 passed.
- Base + head's tests only (upstream/main sources with the PR's tests/): 36 failed, all in test_group_rejects_non_ascii_numbers_and_stays_in_sync (every position x -5, +3, 1_0, U+0661 x 3 chunk sizes); so the new tests fail on the base and pass on the head (run, not just reading).
- Docstring: "NNTPDataError: If the reply can't be parsed" still true.
- No merge conflict with the other open PR heads (#168-#176; git merge-tree).

## Notes (not findings)
- Style: nntp.py already has `_DIGITS_RE = [0-9]+` (used in _select(), nntp.py:1388). The PR uses a second idiom (`isascii() and isdecimal()`); #174 uses the same idiom in utils.py (which cannot import nntp.py's regex). Could be one helper; cosmetic.
- Test name says "non_ascii_numbers" but most cases are signs/underscore; cosmetic.
- Same class of laxness remains elsewhere, outside this PR's scope (pre-existing): listgroup `int(line)` (nntp.py:1329, accepts "+5", "1_0", non-ASCII digits; negatives and 0 are rejected by `number < 1`), over/xover `int(parts[0])` (nntp.py:1670, accepts negative or padded article numbers), and the LAST/NEXT/STAT path already uses _DIGITS_RE. A hostile server only; Low.
- group() does not check first/last/total consistency (e.g. last < first - 1); out of scope.

## Not checked
Integration tests, other Python versions, async/aio variants (none present in the tree), real servers.
