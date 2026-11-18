# Round 0 review: PR #170 (fix/159-stray-yend, 0fa3480) by hk-r0-sonnet-a

Method: read the net diff `upstream/main...origin/fix/159-stray-yend` (47728a7 and its revert 0fa3480 leave no trace in it; confirmed: no zlib-end change in the diff), the head's `_decode_yenc` and `_info_yenczlib`, the new tests, the PR body and issue #159. No host run; nothing here claims tests passed.

Score: 8.5 / 10. Findings: 1 Low in the change (PR text), 1 Low pre-existing (not caused by it).

## What the change does
1. Article path: `_decode_yenc` checks `=yend` only while a block is open (`elif open_block and ...`, nntp.py:1471); a stray one is dropped like other text outside a block. This is #159.
2. XZVER/XZHDR path (not in the issue text, same bug class): `_info_yenczlib` ignores every line after the first `=yend` until the terminator, except a second `=ybegin ` which now raises NNTPDataError ("second =ybegin after the trailer"). The inflate loop moved into `_inflated_lines()` (pure refactor, identical logic).

## Findings

### F1 (Low, new in the change): PR body and title describe only the article path
GitHub body of #170 says "`_decode_yenc()` checks a =yend trailer only while a block is open", "27 of them fail on main", and lists no XZVER/XZHDR change. The head has two more behaviour changes in `_info_yenczlib` (nntp.py:559-576): data after the first `=yend` is no longer decoded or fed to inflate, and a new error for a second `=ybegin`. A reviewer who reads only the body will not look at them. Not a code bug; fix the body (and the "27 tests" count, now stale) or split the XZVER part into its own PR, since "one concern" is arguable (same bug class, different reader).

### F2 (Low, pre-existing, outside this change): a missing =yend before a later =ybegin goes unnoticed
nntp.py:1469: `=ybegin` while `open_block` is True resets decoder/size/crc without recording "missing =yend" for the block it abandons. Input: body with block 1 (no `=yend`), then a complete block 2. Result: no NNTPYEncError, block 1's size/CRC is never checked, and its data is joined into the result. Who triggers: a truncated/damaged multipart post or a hostile server; harm: unchecked (possibly damaged) data returned silently. `open_block` at EOF is reported, only the in-the-middle case is not. Verified by reading; not run. Not for this PR, but it is the same function and the new `open_block and` condition makes the gap easy to fix there (`error = error or "missing =yend trailer"` in the `=ybegin` branch if `open_block`).

## Checks (by reading)
- Stray `=yend` before any `=ybegin`: now ignored, then `not seen_block` still raises "no =ybegin line", so a body with only a stray trailer is still an error.
- A bad real block still errors (test_yenc_stray_trailer_does_not_hide_bad_block); first trailer wins, a later stray one cannot replace it.
- In yEnc, "=y" cannot appear inside encoded data (escape targets are `@ J M }`), so ignoring lines that start `=yend` after the trailer cannot swallow data.
- XZVER: the data cut off by an early `=yend` is caught by the existing `inflate.eof` check (test_xzver_early_yend_in_data); base accepted this stream, so it is a behaviour change, but only for a server that sends `=yend` in the middle of its data. Base would also have failed on a real second block (the `=ybegin` line was fed to the decoder as data), so the new error is a better message, not a new rejection.
- `_inflated_lines`: same loop as before, `data` rebinding is local; `_lines(buf)` checks line length as before.
- All XZVER rows are yielded before the trailer/second-block/eof errors, as with the other trailer errors; connection is marked broken on the error (tests assert NNTPSyncError afterwards), terminator was read, so it is a safe but conservative choice.
- New tests would fail on base: stray-yend rows (base replaced the trailer), second-block rows (wrong error), article stray-trailer rows. test_xzver_early_yend_in_data "valid" passes on base too but documents the change.

## Notes (non-findings)
- `startswith(b"=yend")` also matches `=yendfoo`; pre-existing and harmless.
- helpers.yenczlib got an `after` parameter; tests only.

## Not checked
No host run. Did not diff the XZVER format against a real commercial server stream.
