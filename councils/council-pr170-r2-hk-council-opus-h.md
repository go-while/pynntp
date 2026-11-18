# Council r2: PR #170 (issue #159, stray =yend), hk-council-opus-h

Head 4c945f5, base upstream/main 2bfca17. Fix delta reviewed: `git diff eb5c5aa..4c945f5`
(commits 998b133, 4c945f5). I reviewed by reading only. Nothing was run locally (G1) and I did no host run,
so this review does not claim any test passed.

## Round-1 findings

| # | Sev | Finding | Status | Evidence (4c945f5) |
|---|-----|---------|--------|--------------------|
| 1 | Med | A whitespace-only data line was treated as blank | **Fixed** | nntp/nntp.py:1500 now counts only `b""`, `b"\r\n"` and `b"\n"` as blank. With the input `=ybegin size=1` / `=yend size=0` / ` ` / `=yend size=1`, the space sets `dropped`. The last =yend goes to `_stray_yend_error` with closed=True, and `check_trailer(size=1 vs 0)` mismatches, so it raises "=yend after data outside a block" with data b"". Test `test_yenc_space_line_is_data_not_blank` (tests/test_articles.py:185) covers this. It would pass silently on eb5c5aa, where `bool(b" \r\n".strip())` is False. |
| 2 | Low | A duplicate trailer after a signature raised | **Fixed** | nntp/nntp.py:189-193. When text was dropped, a stray that matches the last closed block (`check_trailer(line, size, decoder.crc32, part=multipart)`) is accepted. `size` and `decoder` reset only on =ybegin, so after a close they still hold that block's values. With the input `k` / `=yend size=1` / `-- ` / `signature` / `=yend size=1`, the result is b"A". Test `test_yenc_duplicate_trailer_after_signature` (tests/test_articles.py:199) covers this. It raises on eb5c5aa. |
| 3 | Low | The docstring did not list the error, and "since the last block closed" was inaccurate | **Fixed** | nntp/nntp.py:1464-1477. The text now says "since the last =yend (or the start of the body)", which matches the code: `dropped` resets on every =yend, in-block or stray (line 1519). The Raises section adds "a =yend follows text outside a block and does not match the last closed block". |

## New findings in the delta

None.

## Notes (not findings)

- **Base comparison.** The base, 2bfca17, checked every =yend against the last block's size and CRC. The head accepts every stray that base accepted (all matching strays) and also accepts non-matching strays when no text came before them. Neither the whitespace change nor the duplicate rule makes the head reject an input that base accepted.
- **Crafted input can still drop data.** A hostile server or poster can send: data, an early =yend that matches the truncated data, more data lines, then the same early trailer again. This is accepted and the later lines are dropped. It cannot be told apart from a signature followed by a duplicate trailer. The sender could just as well post a truncated block, so it is not a new harm.
- **Whitespace lines between blocks.** A whitespace-only line, or a tab line, followed by a non-matching stray =yend now raises, where eb5c5aa ignored it. base raised for this too, and only a broken poster would produce it.
- **Guard before any block.** `closed=seen_block` stops `=yend size=0` from being accepted as a "duplicate" before any block. Accepting it would have been harmless, but the guard is right.
- **Helper docstring.** `_stray_yend_error`'s docstring says "dropped: Text was dropped since the last =yend" and leaves out "(or the start of the body)". This is cosmetic.
- **Changed test.** `test_yenc_stray_trailer_after_blank_lines` changed from " \r\n" to "\r\n". This is consistent with the new rule.

## Not checked

- No host run.
- The XZVER/XZHDR stray-=yend path (nntp/nntp.py:565-589) and the other commits in the branch beyond eb5c5aa..4c945f5.
- How the reader yields lines (bare-LF and CR-only endings), apart from what the code shows.
- Multipart duplicate trailers, beyond reading that `part=multipart` is passed through.

## Score

9.6. All three round-1 findings are fixed and each has a regression test that fails on eb5c5aa. The delta adds no new bug.

#170 r2: 9.6, 0 findings (H/M/L): -
