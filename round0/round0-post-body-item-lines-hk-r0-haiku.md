# Round 0 review: fix/post-body-item-lines (head d6f9408, base upstream/main 2bfca17)

Reviewer: hk-r0-haiku (Haiku 5.5, high). Review by reading only; no build, test or host run.
Read at head with `git show d6f9408:<path>` (the primary checkout is on fix/xr-reading, not on the head).
Scope: `git diff upstream/main...d6f9408` (nntp/nntp.py, tests/test_posting.py).

## Findings

### F1 (Low, pre-existing, not changed by this diff): each body item ends a line, so chunked sources get inserted line breaks
- Where: nntp/nntp.py:171-180 (`_item_lines`) and :1912-1925 (`_prepare_article`), head d6f9408.
- Trigger: a caller passes a body iterable of raw byte chunks, not lines, e.g.
  `post(h, (f.read(8192) for ...))`, or a decoder/generator that yields `b""` when it has no output yet.
  An item without LF ends its line, and an empty item is an empty line.
- What goes wrong: a chunk boundary inside a line becomes a CRLF in the article, and every empty chunk becomes a blank line. `[b"abc", b"", b"def\n"]` is sent as `abc\r\n\r\ndef\r\n`. The article is silently altered; no error is raised.
- Confirmed by reading. Not new: the base also ended a line at each item and sent `b""` as an empty line. The diff now pins this in tests (test_posting.py:210-225, the cases `[b"a", b".b", b"c\n"]` and `[b"", b"x\n"]`, with the comment "as before").
- Severity is Low because the documented contract says "iterable of byte lines" and a chunk source is a caller misuse. It is still silent. Suggest the docstring say "one line per item, not chunks", or the caller joins chunks first.

## Notes (not findings)
- The change itself looks correct on reading. LF split via BytesIO keeps the LF, `removesuffix(b"\r")` after stripping LF, dot-stuffing now runs per line (after the split, before CR/NUL check), CR/NUL check still runs on every line, and `_prepare_article` builds the whole article before `command()`, so a bad item or a read error sends nothing (also when the iterable raises mid-way; test_post_body_read_failure_sends_nothing covers it).
- `itertools` is imported at head (line 22); `Iterable` is only in TYPE_CHECKING and only used in annotations, so no runtime NameError.
- str and bytes bodies go through the same BytesIO path as before; the iterable path is only taken for non-bytes, non-str bodies.
- Items that are str in an iterable: now TypeError from io.BytesIO instead of from startswith; same class, nothing sent. Unchanged in effect.
- bytearray or memoryview as the whole body (not in the declared type): failed before (AttributeError on int items) and still fails (TypeError); nothing is sent either way.
- A CR at the end of one item and LF at the start of the next (`[b"a\r", b"\nb"]`) still raises NNTPDataError, as before. A CRLF split across items is refused, not joined.
- Header lines starting with "." (out of scope per the brief) and issue #166 items were not re-checked.
- Test discrimination by reading: the 5 cases in test_post_body_item_lines_are_split fail on the base for cases 1-3 (`x\n.\nQUIT\n` gives `x\r\n..`; `a\nb\r\n.c\n` gives `..c`; `x\n\n` gives an empty line) and pass on the base for cases 4-5 (regression guards). The 4 cases in test_post_iterable_illegal_chars_sends_nothing pass on the base too (they guard the new path). Base failure is by reading only, not run.
- Test gap: ihave() with an iterable body is not tested; the path is shared through _transfer/_prepare_article, but only post() has iterable tests.
- Not measured: a large number of tiny items now costs one generator and one BytesIO each; likely a constant-factor slowdown, no unbounded growth found.

## Not checked
- No host run (none needed for a finding; base failures are by reading). No build, ruff, mypy or pytest (forbidden locally, G1). No run on test host 117.
- Rest of nntp.py outside the changed hunks; the integration tests (tests/integration/inn2) that post str bodies.
- The other round-0 reviewer's report and the drafts/ notes were not read, to keep this review independent.

score 9, 1 findings (H/M/L: 0/0/1)
