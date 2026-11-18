# Council r1: PR #169 (fix/156-post-msgid, head eaa79ed), reviewer hk-council-opus-f

Base upstream/main 2bfca17. Reviewed: net diff, `post()`/`_transfer()` at the head, `_MESSAGE_ID_RE` (nntp.py:66), the
tests. I also checked the 240 reply texts in local server sources: INN nnrpd/commands.c:840 `"%d Article received %s"`,
NewsCache `240 Article posted`, nntpcache `240 Article posted`, rocksolid-light `240 Article received OK (posted)`. All
give the intended result. By reading only; no host run.

Score: **9.5**

## Findings
None.

## Checks
| Check | Result |
|---|---|
| One concern | Yes (two commits, same rule). |
| Fails on base, passes on head (by reading) | The `report abuse to <abuse@example.net>` cases, `not-an-id <...>`, `(<new@id>)`, `prefix<new@id>`, `<new@id>suffix` and the 249-char case all returned a match on base (`search`) and return True on head. The added `client.date()` checks that the connection stays in sync. |
| Edge cases | Empty reply ("240") gives True. INN with an empty idbuff ("Article received ") gives True. Case-folded prefix. Inner "<" (allowed by RFC 3977 and the regex). The 250-octet limit at both sides. |
| Docstring | "first reply token or follows INN's "Article received" prefix" matches nntp.py:1814-1819. |

## Notes (not findings)
- nntp.py:1814-1819: the new rule drops an id that a server puts later in the text, e.g. `240 Article posted <id>`. Base returned that id; head returns True. No server in the local sources or the test table (INN, Diablo, OUS, NewsCache, go-pugleaf, nntpcache, rocksolid-light) does this, so this is not a finding. Before release, a check against the large commercial backends (Highwinds/Typhoon and similar) would settle it, since callers that build NZBs from the returned id would silently lose it there.
- This is a design trade-off. Accepting a last-token id would bring back the abuse-address case, so the current rule is the safer choice.

## Not checked
No host run. Did not check real replies from commercial providers. `ihave()` is unchanged.
