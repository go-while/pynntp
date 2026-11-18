# Council r2b: fix/post-body-item-lines @ 2ddb15b (hk-council-opus-d, Claude Opus 5.5)

Base upstream/main 2bfca17. Commits reviewed: d6f9408 and 2ddb15b. I reviewed by reading only, with no host run, so I make no claim that tests pass.

## What I checked
- `_item_lines()` (nntp/nntp.py:171-180) and `_prepare_article()` (:1896-1930). Each iterable item is split at LF with `io.BytesIO(item)` iteration. An empty item yields one empty line (as before), and an item without LF ends its line. str and bytes bodies keep the old `io.BytesIO(body)` path.
- After the split, dot-stuffing, LF/CRLF stripping and the CR/NUL check run per real line. This closes the hole where `[b"x\n.\nQUIT\n"]` sent a bare-LF "." line inside the article, which a bare-LF-tolerant server takes as the end of the article. The rest would then be read as commands.
- CRLF inside an item (`b"a\nb\r\n.c\n"`) splits correctly. A CR split across items (`b"a\r"`, `b"\nb"`) still raises CR/NUL before anything is sent, as before, and the docstring now says items must be complete lines.
- Everything is still prepared before `command()` in `_transfer()`, so a bad item raises with nothing sent. The tests check `sock.sent == b""` and a follow-up DATE.
- `ihave()` shares `_transfer`/`_prepare_article`, and a new test covers it.
- Wrong item types (str, or ints from a bytearray body) still raise TypeError or AttributeError before anything is sent, as on the base, so nothing fails silently.

## Findings
None.

## Notes (not findings)
- Each item gets its own `BytesIO`. For a binary file of many short lines, that is a constant per-line overhead in the preparation loop. It stays linear and bounded. An optional fast path would be to `yield item` when `b"\n" not in item[:-1]`.
- Behaviour change for callers who passed multi-line items: these are now split and dot-stuffed per line, which is what they meant. Worth a line in the release notes.

## Not checked
- No host run.
- A body over `_SPOOL_SIZE` built from multi-line items, by test. By reading, the spool path does not depend on the split.

## Score
9.6. It is one concern, fixes a real early-end and command-injection path, has good edge-case tests (CR/NUL after the split, empty item, item without LF, ihave), and the docstrings are clear.
