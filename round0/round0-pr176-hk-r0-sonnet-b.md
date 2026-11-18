# Round 0, PR #176 (fix/165-range-bool, head 84d63fb), reviewer hk-r0-sonnet-b

Score: 9/10. Findings: none.

## What I checked
- Net diff vs upstream/main 2bfca17 (the 52b24bc + revert pair cancels; the net diff is what is listed here): utils.py unparse_range() raises ValueError("Invalid range format") if any tuple bound is a bool; nntp.py _xover() computes args (unparse_msgid_range) before it touches overview_fmt; tests in test_commands.py and test_utils.py.
- Coverage of callers: unparse_range/unparse_msgid_range is the only range formatter (nntp.py:1513 listgroup, 1804 _hdr, 1927 _xover, 2043 xpat), so one change covers over/xover/xzver/hdr/xhdr/xzhdr/xpat/listgroup. A bare bool was already rejected (falls to "Must be an integer or tuple"); the tuple case is now consistent.
- The _xover reorder is needed: the test asserts nothing is sent, and `self.overview_fmt` would send LIST OVERVIEW.FMT first. Side effect: an invalid range now fails before the format request (no cached format on a failed call); an improvement, and still one concern ("reject before sending").
- Host 116, head: 1048 passed. Base sources + head's tests: 14 failed (3 test_over_rejects_boolean_bounds_before_sending x 3 chunk sizes, 5 test_unparse_range_rejects_boolean_tuple_bounds); new tests fail on base, pass on head (run).
- Docstrings: unparse_range() "ValueError: If obj is not one of those forms" still true.
- No merge conflict with the other open PR heads.

## Notes (not findings)
- The check is only for bool; other wrong element types still get formatted and sent: (None,) -> "None-", (1.5, 2) -> "1.5-2", ("a",) -> "a-", negative ints. The issue was about bool only and those mostly end in a loud 501 from the server, so caller-mistake-with-silent-harm is not shown; an `isinstance(b, int)` allow-list would be the complete form. Low.
- over()/xover()/hdr() "Raises:" sections do not list ValueError (pre-existing, but this PR adds another way to get it).
- Bounds are not checked for order or range (e.g. (5, 1)); out of scope.

## Not checked
Real servers' reaction to "True-" (not needed for the verdict), integration tests.
