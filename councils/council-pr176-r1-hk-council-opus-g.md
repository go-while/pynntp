# Council r1: PR #176 (fix/165-range-bool, head 84d63fb) — hk-council-opus-g

Base upstream/main 2bfca17. Fixes #165. Commits e7dff3d, 52b24bc and its revert 84d63fb (net diff = e7dff3d). Reviewed by reading only (G1); no host run, so no claim that tests pass.

## Score: 9.5 — 0 findings

## Findings
None.

## What I checked
| Check | Result |
|---|---|
| Change | nntp/utils.py:54-55: unparse_range() raises "Invalid range format" if any item of a range tuple is a bool. nntp/nntp.py:1649-1654: `_xover()` formats the range before reading `overview_fmt`, so a bad range raises before LIST OVERVIEW.FMT is sent. |
| Issue inputs | `(True,)`, `(False,)`, `(False, 1)`, `(1, True)`, `(True, False)` raise ValueError; bare `True` was already rejected. |
| Other callers | listgroup(), `_hdr()` (HDR/XHDR/XZHDR) and xpat() already format the range before any command, so with the utils change no range-taking command sends anything for a bool bound. over()/xover()/xzver() go through `_xover()`. |
| Side effect of the reorder | Strictly better: any invalid range (wrong type, bool) no longer triggers and caches LIST OVERVIEW.FMT first. Valid calls send the same commands in the same order (LIST OVERVIEW.FMT only on the first call, then OVER). |
| Test fails on base / passes on head (by reading) | tests/test_commands.py:26: on base, over((True,)) first sends LIST OVERVIEW.FMT and hits EOF in the fake socket (not ValueError), and `sock.sent` changes -> fail; head raises ValueError with nothing sent. test_utils.py case: base returns "True-"/"False-1" -> fail. |
| One concern | Yes; the revert removes the wider "reject all invalid range items" change, which stays a note in #166. |
| Typing | The tests type `bounds` as `tuple[int, ...]`, which is not assignable to the fixed-length `Range` tuples, so the `# type: ignore[arg-type]` comments are used (no unused-ignore under mypy --strict). |
| Merge with the other open PRs | No textual conflicts (`git merge-tree`). |

## Notes (not findings)
- over()/xover()/hdr()/listgroup() docstrings list no `ValueError` for an invalid range; pre-existing for every range-taking method, not new here.
- Other non-int items (`(1, None)` -> "1-None", `(1.5,)`, negative numbers) still go to the server; deliberately out of scope after the revert (server rejects them; #166 note).
- Known, skipped: #179 (bool as a message-id/article argument, e.g. article(True)).

## Not checked
- No host run.
