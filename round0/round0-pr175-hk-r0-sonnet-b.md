# Round 0, PR #175 (fix/164-overview-format, head b0cc064), reviewer hk-r0-sonnet-b

Score: 9/10. Findings: none.

## What I checked
- Net diff vs upstream/main 2bfca17: nntp/utils.py parse_overview_fmt() (+2 lines: fullmatch of `_HEADER_NAME_RE` `[!-9;-~]+` on the name after the metadata swap), tests in test_commands.py and test_utils.py. One concern, matches issue #164.
- utils.py:153-160 at the head: order is right: split on ":", metadata swap (":bytes" -> "bytes"), then validate. ":" (empty), " :full", "Subject :full" are rejected; "Subject: " / "Xref:full " / ":bytes " still pass because of the existing `rstrip()` (the PR adds tests for them). ":full" alone swaps to name "full" (valid, as before).
- list_overview_fmt() (nntp.py:1236) wraps the call in `_data_errors`, so a bad line raises NNTPDataError mentioning "LIST OVERVIEW.FMT" (the test matches `OVERVIEW\.FMT`). A raise in `_overview_fields` (cached_property) is not cached, so a later call retries; the connection is marked broken like for other parse errors.
- Host 116, head: 1049 passed. Base sources + head's tests: 12 failed (3 in test_overview_fmt_rejects_invalid_name x 3 chunk sizes, 3 in test_parse_overview_fmt_rejects_empty_or_padded_name); the three "still accepted" cases are not failing on base by design (regression tests). New tests fail on base, pass on head (run).
- Docstring: still "ValueError: If the line cannot be parsed"; fine.
- No merge conflict with the other open PR heads.

## Notes (not findings)
- Behaviour change for broken servers: before, an odd OVERVIEW.FMT line was accepted and over() worked with odd keys; now over()/xover() fail on every call (LIST OVERVIEW.FMT is re-sent each time since nothing is cached, and each failure breaks the connection) until the server is fixed. That is what the issue asked for (malformed server data); real servers send plain "Name:" / "Name:full" / ":bytes", so I see no normal-operation harm. Low.
- Not covered and pre-existing: duplicate field names (nntp.py:1678 comment says names are unique per LIST OVERVIEW.FMT, nothing enforces it), more than one ":" in a line (bare unpack ValueError, still reported as NNTPDataError).
- A "Name: full" (space before suffix) line is rejected as unknown suffix (pre-existing, RFC-conform).

## Not checked
Real servers' OVERVIEW.FMT output other than the RFC forms, integration tests.
