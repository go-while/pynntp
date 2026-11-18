# Council r1: PR #174 (fix/158-number-value, head 9004229) — hk-council-opus-g

Base upstream/main 2bfca17. Fixes #158. Commits cfac120 + 9004229. Reviewed by reading only (G1); no host run, so no claim that tests pass.

## Score: 9.5 — 0 findings

## Findings
None.

## What I checked
| Check | Result |
|---|---|
| Change | nntp/utils.py:183-190: parse_number_value() gives 0 only for a token that fully matches `_MESSAGE_ID_RE` (moved from nntp.py to utils.py:34, imported back at nntp.py:39), and only if `allow_msgid`; otherwise the token must be ASCII decimal; everything else raises ValueError. nntp.py:1572-1590 and 1768-1770: `_hdr()` (HDR/XHDR/XZHDR) and xpat() pass `allow_msgid=isinstance(msgid_range, str)`. |
| Issue inputs | `<broken`, `<>`, `<a>b>`, `-1`, `+1`, `1_0`, `١` rejected; a message-id row for a range, a single number or the current article (None) rejected. |
| Real servers | HDR by message-id answers `0 value` (RFC 3977 8.5) -> digits, still fine. INN's XHDR/XPAT by message-id echo `<msgid> value` -> allowed because the request was a str. Range and current-article requests are answered with article numbers by INN, so they are unaffected. |
| Error path / sync | Errors are raised inside `_data_errors`, which marks the connection broken while a response is being read (pre-existing, documented in NNTPSyncError). |
| Public API | `parse_number_value(line, allow_msgid=True)`: default keeps old callers working for valid input. `_MESSAGE_ID_RE` stays reachable as `nntp.nntp._MESSAGE_ID_RE`; post() (and #169's version of it) still resolve the name after a merge. |
| Docstrings | hdr()/xpat() Raises and parse_number_value() Args match the code. |
| Test fails on base / passes on head (by reading) | tests/test_commands.py:329, 343, 354: base yields (0, ...) or int("-1") etc. without raising -> fail; head raises. tests/test_utils.py new cases: base has no `allow_msgid` (TypeError, not ValueError) or accepts the token -> fail. :366 is a regression guard that passes on both. |
| One concern | Yes (the regex move is needed for it). |
| Merge with the other open PRs | No textual conflicts (`git merge-tree`). |

## Notes (not findings)
- Test gap (small): at command level the malformed-message-id rows (`<broken`, `<>`) are only tried on a range request (test_commands.py:329), where allow_msgid=False would reject them even without the regex. The case the regex exists for, a malformed message-id row in the answer to a request by message-id, is covered only by the unit test in test_utils.py. One more parametrized case `xhdr("Subject", "<a@b>")` answered by `<broken value` would pin it end to end.
- XZHDR has no own test; it goes through the same `_hdr()` path.
- Behaviour change to be aware of: a request by message-id whose echoed id is longer than 248 characters or contains 8-bit bytes now raises (and breaks the connection) where it used to give (0, value). Such ids are invalid under RFC 3977/5536 and INN refuses them in the command, so I found no valid-configuration trigger.
- Same isascii/isdecimal vs `_DIGITS_RE` remark as for #173: pick one idiom for both PRs.
- Known, skipped: #179 (caller-side message-id validation; `unparse_msgid_range` passes any str unchanged).

## Not checked
- No host run. Other servers (Diablo, Typhoon, Highwinds, NNTPChan, etc.) answering XHDR/XPAT with a range or the current article in message-id form: I know of none, but did not verify.
