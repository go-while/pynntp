# Council review: PR #174 follow-up e339eda (allow_msgid keyword-only)

Reviewer: hk-council-opus-174k (Claude Opus). Read-only; nothing run (G1).
Checkout: /claude/projects/pynntp/pynntp-tools/council-174k/checkout (HEAD e339eda).
Delta 9004229..e339eda: 2 files, 1 line each.

## Findings

None.

## Checks done

| Check | Result |
|---|---|
| Positional callers of `allow_msgid` | None. Searched the whole checkout for `parse_number_value` and `allow_msgid`. The only library caller is nntp/nntp.py:1588, which now passes `allow_msgid=allow_msgid`. Tests: tests/test_utils.py:282, 291, 299, 304 call `parse_number_value(line)` with no flag; :310 and :314 already pass `allow_msgid=False` by keyword. No docs/README mention the function except CHANGELOG.md:8 (name only). |
| Public API vs upstream 3.3.0 | `upstream/main:nntp/utils.py:162` is `def parse_number_value(line: str) -> tuple[int, str]`. No release ever had `allow_msgid`, so no user can pass it positionally. Adding an optional keyword-only parameter is purely additive: every 3.3.0 call `parse_number_value(line)` stays valid with the same result (default `True` accepts message-id rows as 3.3.0 did). Keyword-only is the safer shape for a new public flag because it keeps the positional signature unchanged. |
| Behaviour change | None. The parameter value reaching the function is the same as at 9004229; only the way it is passed changed. `_number_values()` (nntp/nntp.py:1578-1589) and its two callers (:1572-1576 hdr/xhdr/xzhdr, :1768-1770 xpat) are unchanged and already pass `allow_msgid` by keyword. |
| Ruff with #177 | The reason is real: #177 sets `select = ["ALL"]` with per-file ignore `FBT` only for nntp/nntp.py and `FBT001` for tests/*, so a positional bool with default in nntp/utils.py would trip FBT001/FBT002. The still-positional `allow_msgid: bool` of the private `_number_values()` (nntp/nntp.py:1579) is covered by the nntp/nntp.py `FBT` ignore, so it needs no change. |
| Line length / format | nntp/nntp.py:1588 is 87 characters, under ruff's default 88 (no `line-length` set). Consistent with the lead's report that ruff format passes. |
| mypy | Keyword call matches the keyword-only parameter; nothing to flag. |

## Notes (not findings)

- The PR has no "Unreleased" CHANGELOG entry for the new `allow_msgid` parameter or for the stricter HDR/XHDR/XPAT row checks. That is about the PR as a whole, not this commit; leave it if the maintainer writes the changelog at release time.
- Lead's facts (full check on a test host for #174 alone and merged with #177, 1133 unit tests) were not re-run by me, as G1 requires; my reading agrees with them.

## Score

10/10. A minimal, correct change that keeps the public API additive relative to 3.3.0 and removes a known conflict with #177.

#174 e339eda: 10, 0 findings (0/0/0): -
