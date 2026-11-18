# Round 0 review: PR #176 (fix/165-range-bool)

Reviewer: hk-r0-haiku-b (round 0, read-only). Head 84d63fb, base upstream/main 2bfca17.
Net content: the head tree equals e7dff3d (`git diff e7dff3d origin/fix/165-range-bool` is empty). 52b24bc (reject invalid range items) and its revert 84d63fb cancel out. The reviewed change is e7dff3d: reject bool bounds before any command.
Scope: nntp/utils.py unparse_range (about 51-60), nntp/nntp.py _xover (about 1644-1651) and every range path (listgroup 1317, hdr 1572, _xover 1651, xpat 1758).
Method: reading only. No builds, tests or host runs (G1). "Fails on base" is by reading.

One concern: a bool inside a range tuple must be rejected before a command is sent.

## Findings

None.

## Test by reading

- test_unparse_range_rejects_boolean_tuple_bounds: (True,), (False,), (False, 1), (1, True), (True, False). Base formats them as "True-", "False-", "False-1", "1-True", "True-False" without raising, so the test fails on base. Head raises "Invalid range format", which matches "range".
- test_over_rejects_boolean_bounds_before_sending: on base, _xover formats the range, then reads overview_fmt, which sends LIST OVERVIEW.FMT before the range error. sock.sent changes, and the ValueError is not what the test expects, so it fails on base. On head the range is formatted first (nntp.py:1650-1651), so nothing is sent.
- The bare-bool case (`True`) was already rejected on base (utils.py: `isinstance(obj, int) and not isinstance(obj, bool)`, then "Must be an integer or tuple").

## Checked

- Ordering: on head the args are built before self.overview_fmt (nntp.py:1654), so a bad range sends nothing and does not cache or issue LIST OVERVIEW.FMT.
- Every range path goes through unparse_range or unparse_msgid_range, so the bool check covers listgroup, hdr, xhdr, over, xover and xpat.
- Docstring of unparse_range ("ValueError: If obj is not one of those forms") matches.

## Notes (not findings)

- The issue's harm is "OVER True-" on the wire. The server answers with a syntax error (a permanent 5xx, NNTPPermanentError), so the failure is loud. By the brief this is a caller mistake that fails loudly, so it is not a finding. The guard is still a correct hardening.
- Other wrong-type bounds, such as (1.5,), (None,) or (-5,), are still formatted and sent. The server rejects them loudly, so they are not findings either.
- The two commits 52b24bc and 84d63fb cancel out. Only e7dff3d's content is in the net diff.

## Not checked

- No test, ruff or mypy run. No host run.
- Exact behavior of the fake socket in the test on base (the failure on base follows from the sent-bytes and exception checks either way).

## Score

9.5 (ready as is; a targeted, well-tested guard).
