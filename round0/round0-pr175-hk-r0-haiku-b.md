# Round 0 review: PR #175 (fix/164-overview-format)

Reviewer: hk-r0-haiku-b (round 0, read-only). Head b0cc064, base upstream/main 2bfca17 (head = 5d361f7 + b0cc064 on the fork branch; the net diff against base is what is reviewed).
Scope: the net diff (nntp/utils.py +2, tests +20) and the head path list_overview_fmt -> parse_overview_fmt -> _overview_fields -> over()/xover().
Method: reading only. No builds, tests or host runs (G1). "Fails on base" is by reading.

One concern: an OVERVIEW.FMT field name must be a non-empty run of header-name characters, with no space and no colon.

## Findings

1. Low. A single odd name in LIST OVERVIEW.FMT now fails every OVER/XOVER on that connection, where base worked.
   - Where: utils.py:156-157 (raise for an invalid name) and nntp.py:1238-1239 (_data_errors around parse_overview_fmt), with _overview_fields (nntp.py:1630-1632), which caches nothing on an error.
   - Trigger: a server (broken, or using a name outside the header-name grammar) whose LIST OVERVIEW.FMT has an empty name (`:`) or a padded name (` :full`, `Subject :full`).
   - What goes wrong: the NNTPDataError is raised while the 215 block is being read, so _data_errors sets _broken. Every later command raises NNTPSyncError until reconnect(). A reconnect gets the same list from the same server, so OVER/XOVER stay unusable on that server.
   - Base gave: `:` a key "", and ` :full` / `Subject :full` a key with a space, with "full" values left unstripped ("Subject: ..."). That is silent wrong data, which the PR removes.
   - So the PR trades silent wrong values for a loud, per-server total failure of overview. The direction is right, but a fallback (skip the bad line, or use the RFC 2980 default format) would keep overview working. Confirmed by reading.
   - Pre-existing in form (the bad-line handling), new in effect.

## Test by reading

- test_overview_fmt_rejects_invalid_name (`:`, ` :full`, `Subject :full`): base yields ("", False) or ("Subject ", True) without raising, so it fails on base. On head it raises NNTPDataError with "LIST OVERVIEW.FMT line" in the text, which matches r"OVERVIEW\.FMT".
- test_parse_overview_fmt_rejects_empty_or_padded_name: same three inputs at unit level. Fails on base, passes on head.
- New parametrized cases in test_parse_overview_fmt (`Subject: `, `Xref:full `, `:bytes `): they pass on base too (rstrip). They are regression guards, not fail-on-base tests.
- _HEADER_NAME_RE (utils.py:30, `[!-9;-~]+`) excludes space and colon, so the check is exactly "no empty, no space, no colon, no control". rstrip() keeps the leading space in ` :full`, so that case is rejected, as the test expects.
- The LIST helper (list() -> info()) does not strip lines, so ` :full` reaches parse_overview_fmt with its leading space. The test depends on this, and it holds.

## Notes (not findings)

- Trailing whitespace on a line is still accepted (rstrip), and `:bytes ` gives "bytes". Correct.
- The swap for metadata names (`:bytes` -> name "bytes") runs before the check, so `:bytes` is valid and `::` or `:` are not.
- parse_overview_fmt is called only from list_overview_fmt (nntp.py:1239), so no other caller sees the new exception.

## Not checked

- No test, ruff or mypy run. No host run.
- Whether any real server emits names with spaces or empty names (no survey).
- The overview_fmt caching path when the first call fails and a later call succeeds after reconnect (only read as far as _overview_fields).

## Score

8 (the fix is correct; the open question is the loud failure of all overview calls for a server with one odd name, which the lead may want to soften).
