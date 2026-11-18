# Round 0 review: PR #174 (fix/158-number-value)

Reviewer: hk-r0-haiku-b (round 0, read-only). Head cfac120, base upstream/main 2bfca17.
Scope: the net diff (nntp/nntp.py, nntp/utils.py, tests) and the head parse path for HDR, XHDR, XZHDR, XPAT: nntp.py _hdr/_number_values (about 1567-1582), _data_errors (about 596-607), utils.py parse_number_value (about 164-186).
Method: reading only. No builds, tests or host runs (G1). "Fails on base" is by reading.

One concern: a first token starting with "<" must be a well-formed message-id, and any other first token must be ASCII decimal.

## Findings

1. Low. Pre-existing, not fixed by the PR. A well-formed message-id row in a numeric-range answer still gives article number 0, silently.
   - Where: utils.py:180-181 (`if _MESSAGE_ID_RE.fullmatch(first): number = 0`), used by nntp.py:1580 for every HDR/XHDR/XPAT row.
   - Trigger: a broken server (or a server that answers a numeric-range query with message-id rows) replies `HDR Subject 1-10` with `<a@b> value` rows. parse_number_value has no context and gives 0, and _number_values does not check whether the query was by message-id.
   - Harm: each value gets article number 0, so the caller cannot tell which article it belongs to. No error is raised.
   - Confirmed by reading. The issue #158 text asks for this too ("also in range queries where a message-id row can't be the answer"), so the PR covers only the first half of the issue.

## Test by reading

- test_header_rows_reject_invalid_identifiers: hdr, xhdr and xpat, each with `<broken`, `<>`, `-1`, `+1`, `1_0`. Base returns rows (0 or -1 or 1 or 10), so no NNTPDataError is raised and the test fails on base. On head each raises through _data_errors.
- test_parse_number_value_rejects_invalid_identifier: `<a>b>` and U+0661 are accepted on base (0 and 1). Fails on base, passes on head.
- test_parse_number_value_valid_message_id (`<id>`, `<a@b>`): passes on base and head. This is a regression guard.
- `_MESSAGE_ID_RE` moved from nntp.py to utils.py and imported back into nntp.py (nntp.py:39). No other user of the old definition exists, and `re` is still used in nntp.py (line 130), so no unused import.

## Notes (not findings)

- Deliberate behavior change, for the lead to accept or not: a first token that starts with "<" but fails _MESSAGE_ID_RE now raises NNTPDataError. _data_errors (nntp.py:596-607) sets _broken while a response is being read, so the connection needs reconnect(). On base such a row gave 0 and the session stayed in sync. A server echoing a non-RFC message-id (non-ASCII, longer than 248 characters, a stray ">") now costs the session. The failure is loud, not silent, so it is not a finding.
- Numeric-garbage rows (`abc value`, `-1 value`) already broke the connection on base via the same path, so the new behavior is consistent with that.
- Empty line: `first, *value = []` raises ValueError, which becomes NNTPDataError. Same as base.
- Docstrings of hdr/xhdr/xpat ("NNTPDataError: If a line can't be parsed") and of parse_number_value match the code.

## Not checked

- No test, ruff or mypy run. No host run.
- XZHDR and XZVER compression paths beyond the shared _number_values route.
- Whether any real server echoes non-RFC message-ids. This is a judgment, not a survey.

## Score

8 (the range-query half of #158 is still open, and the connection-breaking trade-off needs a decision).
