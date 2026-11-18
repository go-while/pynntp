# Council R2b — 5: fix/post-body-item-lines

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `2ddb15bf9b61401e2793ff66b9c363769a74f566`.
Scope: this whole body-item PR, not a header-dot-stuffing change.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

The body splitter at `nntp/nntp.py:171–180` and its use at1912–1926 ensure every
LF-delimited line of an iterable item passes through validation and dot
stuffing. Thus an interior `.` line is sent as `..`, not a premature article
terminator. Both POST and IHAVE use the same preflight function.

Bytes/string bodies keep their existing line iteration. Iterable items
without LF still terminate a line; empty items still mean one empty line.
CRLF normalization is unchanged, and bare CR or NUL anywhere in any item
raises before the network exchange. The spooled temporary-file lifetime,
final terminator and transfer error policy remain unchanged.

The submitted tests include multiple lines, CRLF, interior/empty dot lines,
bad bytes in later lines/items, empty items and an explicit IHAVE wire result.
The public docstring now says to supply complete lines, not arbitrary chunks.

## Notes — not findings

Splitting a CRLF across iterable items is outside the documented complete-line
contract and was already rejected; it is not a new valid-input regression.
No unrelated header behavior is demanded of this focused body fix.

## Verification and limits

Confirmed by reading the whole change and shared transfer callers. No test or
real POST/IHAVE was executed, and no test-pass claim is made for this reviewer.
No tree edits, commits, installs, host jobs or GitHub writes. G1 observed.

5 fix/post-body-item-lines: 10, 0 findings (0H/0M/0L); below 9.5 because: -
