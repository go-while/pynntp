# Round 0, PR #174 (fix/158-number-value, head cfac120), reviewer hk-r0-sonnet-b

Score: 9/10. Findings: none (one Low-unconfirmed item is on the notes list).

## What I checked
- Net diff vs upstream/main 2bfca17: _MESSAGE_ID_RE moved from nntp.py to utils.py (nntp.py imports it back; `re` is still used in nntp.py:130,132, so no unused import; uses at nntp.py:1390, 1810, 1841 still resolve), parse_number_value() now: valid message-id (fullmatch) -> 0; ASCII decimal -> int; else ValueError. Tests in test_commands.py (hdr/xhdr/xpat x 5 tokens) and test_utils.py. One concern, matches issue #158 (the "closing >" and "-1/+1/1_0" parts).
- The ValueError reaches the caller as NNTPDataError through _number_values() -> _data_errors(), which also marks the connection broken (out of sync) while the multi-line response is still being read; consistent with all other parse errors in the module.
- Moving the regex does not change post() (nntp.py:1810) or _select(); _select() already used the same strict fullmatch for STAT/NEXT/LAST, so the PR makes HDR consistent with it.
- Host 116, head: 1088 passed. Base sources + head's tests: 52 failed (hdr/xhdr/xpat x tokens, plus test_parse_number_value_rejects_invalid_identifier x 7); the new tests fail on the base and pass on the head (run).
- Docstring says a message-id first token gives 0 "as HDR gives"; matches code. Raises text matches.
- No merge conflict with the other open PR heads.

## Notes (not findings)
- The issue says message-id rows are wrong "also in range queries where a message-id row can't be the answer". The PR still returns number 0 for a well-formed `<id>` first token in a range query (no knowledge of the query kind in the parser). A hostile server could therefore still feed (0, value) rows to a range query; Low, and the docstring documents the legacy case. Fixing it would need the query kind passed down.
- Possible regression for non-conforming message-ids, unconfirmed: legacy XHDR by message-id echoes the id as first token. An id that is not RFC 3977 3.6 (contains ">" inside, non-ASCII, or over 248 characters between the brackets) used to give number 0 and now raises NNTPDataError and breaks the connection. The id comes from the caller, and servers that store such ids are rare (INN checks ids on input), so I did not file it; I did not test against a real server.
- Importing a private name (`_MESSAGE_ID_RE`) from utils into nntp.py next to `from . import utils`; cosmetic.
- parse_number_value() with an empty line raises a bare unpack ValueError (pre-existing, still caught as NNTPDataError).

## Not checked
Real servers (INN XHDR by message-id behaviour), integration tests, other Python versions.
