# Council r2b: fix/empty-message-id @ ca94d6e (hk-council-opus-d, Claude Opus 5.5)

Base upstream/main 2bfca17. Commits reviewed: be57be3 and ca94d6e. I reviewed by reading only, with no host run, so I make no claim that tests pass.

## What I checked
- `_msgid_article()` (nntp/nntp.py:167-181): None maps to None (current article). bool, `""` and blank strings raise ValueError. Other values go through `str()`. bool is caught before the int path, which matters because bool is a subclass of int.
- Every caller: stat (:1399), article (:1515), head (:1552), body (:1581). `unparse_msgid_range()` (nntp/utils.py:62-82) is used by `_hdr` (hdr/xhdr/xzhdr, :1593), `_xover` (over/xover/xzver, :1689) and xpat (:1796). A bool range there is already rejected by `unparse_range()` ("Must be an integer or tuple"), and the docstrings say "not a valid range".
- Root cause: `_command()` (:701, `f"{verb} {args}" if args else verb`) drops an empty argument, and a blank one becomes trailing spaces that the server ignores. The fix validates before `command()`, so nothing is sent. The tests assert `sock.sent == b""` for all four article methods, the hdr family, xpat and over/xover. `overview_fmt` is fetched first in the overview test, so the empty-send assertion means something.
- None is still the current article, and a new positive test covers this for all four verbs.
- Raises sections were updated on every public method affected.

## Findings
None in the change.

Pre-existing and out of scope, for the issue list (Low):
- nntp/nntp.py:1328/1332 at the head, `listgroup(name="")` or `listgroup(" ")`. Triggered by the calling program with an empty or blank group name, for example from an unset config value. `_command()` drops the empty argument, so `LISTGROUP` is sent bare and the server lists the currently selected group. The caller gets that group's article numbers without any error, believing they belong to the group it asked for. Confirmed by reading `_command()` :701 and RFC 3977 6.1.2 (no argument means the currently selected group). It has the same root cause as this PR but involves a group name rather than a message-id or article argument, so it is not counted against this head. By contrast, `group("")` sends a bare `GROUP`, which gets a 501 and fails loudly, so it is harmless.

## Notes (not findings)
- Behaviour change: callers that passed `""` to mean the current article (for example `body(msgid or "")`) now get ValueError. That is intended, but it deserves a line in the release notes and the right PR label.

## Not checked
- No host run.
- `ihave("")` and `xpat` with an empty header or pattern: they send malformed commands that the server rejects, which is outside this PR.

## Score
9.5. Validation is complete for the stated scope, and the tests cover every entry point, including "nothing sent".
