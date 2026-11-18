# Council r1: PR #175 (fix/164-overview-format, head b0cc064) — hk-council-opus-g

Base upstream/main 2bfca17. Fixes #164. Commits 5d361f7 + b0cc064 (the second puts back `rstrip()` that the first had narrowed to `rstrip("\r\n")`; net diff is only the name check plus tests). Reviewed by reading only (G1); no host run, so no claim that tests pass.

## Score: 9.5 — 0 findings

## Findings
None.

## What I checked
| Check | Result |
|---|---|
| Change | nntp/utils.py:156-157: after the metadata swap, the field name must fully match `_HEADER_NAME_RE` (`[!-9;-~]+`, the RFC 5322 field-name set already used by parse_headers), else ValueError -> NNTPDataError "Invalid LIST OVERVIEW.FMT line: ..." via `_data_errors` (nntp.py list_overview_fmt). |
| Issue inputs | `:` (empty name), ` :full`, `Subject :full` rejected. |
| Real formats | `Subject:` ... `Xref:full`, `:bytes`, `:lines`, RFC 2980 style `Bytes:`/`Lines:`, any case of `full`, and trailing whitespace (`Subject: `, `Xref:full `, `:bytes `) all still parse. |
| Consequence for over()/xover() | `_overview_fields` is a cached_property; a raised NNTPDataError is not cached and marks the connection broken, so over() fails loudly against a server with a bad format line, instead of returning rows keyed `""`/`" "`. That is the behaviour the issue asks for and matches the pre-existing "unknown suffix" error path. |
| Test fails on base / passes on head (by reading) | tests/test_commands.py:269 and the new test_utils.py case: on base `:` -> ("", False), ` :full` -> (" ", True), `Subject :full` -> ("Subject ", True), no raise -> fail; head raises. The trailing-whitespace cases are regression guards (pass on both). |
| One concern | Yes. |
| Docstring | "ValueError: If the line cannot be parsed." still true. |
| Merge with the other open PRs | No textual conflicts (`git merge-tree`). |

## Notes (not findings)
- A line with leading whitespace (` Subject:`) is now rejected instead of being accepted as the key `" Subject"`. Both are wrong for such a server; failing loudly is consistent with the issue. I know of no server that sends this (INN, Diablo, Leafnode send a fixed list).
- Duplicate field names are not rejected (nntp.py comment "names are unique per LIST OVERVIEW.FMT"); pre-existing, out of scope.
- `Xref: full` (space before the suffix) still raises "unknown suffix"; pre-existing, no known server sends it.
- Commit title of b0cc064 ("Preserve trailing whitespace") reads opposite to what it does (it tolerates/strips trailing whitespace); irrelevant after a squash merge, but the PR body/title should not repeat it.

## Not checked
- No host run.
