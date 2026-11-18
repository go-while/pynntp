# Round 0, fix/post-body-item-lines @ d6f9408 (base 2bfca17), reviewer hk-r0-sonnet

Method: read the diff and the full _prepare_article/_transfer/post/ihave and tests/test_posting.py at d6f9408. No host run, nothing executed (G1).

## Findings
Nothing found.

Checked by reading, all fine:
- Change goes through the single funnel _prepare_article (post and ihave both), so both are fixed; str/bytes bodies still use io.BytesIO(body) unchanged.
- Empty item: _item_lines yields b"" once -> one empty CRLF line, same as base. Item without LF: BytesIO yields it whole -> CRLF added, same as base. Item "x\r\n", "x\n": same output as base.
- CR/NUL: checked after the split and after the LF/CRLF strip, per line, so a CR or NUL on any later line of an item still raises NNTPDataError before anything is written to the socket (article is built fully into the spool first). "a\r\r\n" and a lone trailing "\r" still raise, as on base.
- BytesIO splits only at b"\n" (not splitlines: no split at \x0b, \x0c, \x85, \r), so no new line boundaries beyond LF.
- Dot-stuffing happens per split line, so ".\nQUIT\n" inside an item is now stuffed (the bug being fixed).
- Large iterables: itertools.chain.from_iterable(map(...)) is lazy; memory is still bounded by the spool plus one item. Iterator exceptions (OSError mid-iteration) still raise before send (existing test covers it).
- Non-bytes items (str, int from a bytearray body): TypeError/AttributeError before anything is sent, as on base; only the exception type may differ. memoryview items now work (BytesIO accepts them), a small widening.
- Typing: Iterator/Iterable are TYPE_CHECKING imports, fine with `from __future__ import annotations`; local annotation `lines: Iterable[bytes]` is not evaluated.
- One concern: yes, one commit, code + docstrings (post, _prepare_article; ihave says "as for post()") + tests. No CHANGELOG edit, correct per projects/pynntp.md.

## Tests: fail on base, pass on head (by reading, not run)
- test_post_body_item_lines_are_split: cases 1-3 fail on base (base sends "x\n.\nQUIT\r\n", an unstuffed "a\nb\r\n.c\r\n..." with bare LFs, and "x\n\r\n" for b"x\n\n"); cases 4 (no LF) and 5 (empty item) pass on both, as intended regression guards.
- test_post_iterable_illegal_chars_sends_nothing: all four cases also raise on base (the whole item was checked for CR/NUL); they are guards, not red-green. Fine as guards.

## Notes (not findings)
1. No test for ihave() with an iterable body; covered only through the shared _prepare_article. Cheap to add one parametrized case.
2. Per-item io.BytesIO + generator for a binary file body whose items are already single lines adds a small constant per line (a few hundred ns by my estimate, not measured). Could skip BytesIO when b"\n" not in item[:-1] / item.find(b"\n") in (-1, len-1). Optimisation only.
3. Empty-vs-[b""] asymmetry: body b"" sends no line, [b""] sends one empty line (pre-existing, unchanged, tested "as before").
4. An item that is a whole multi-line article with mixed bare-CR line ends still raises CR error (by design).
5. Behaviour change for callers who pass an iterable whose items contain LF mid-item expecting a single line: previously the LF was sent as part of a CRLF-terminated line (a bare LF on the wire, article corrupted for LF-ending servers); now split. This is the intended fix, worth a CHANGELOG line at release time (lead's call; PRs do not edit it).

## Not checked
No test or host run (pytest, mypy, ruff not executed); timing of the BytesIO overhead not measured; real servers (INN, others) not exercised; yEnc-posting flows not traced beyond the funnel.

score 9, 0 findings (0H/0M/0L)
