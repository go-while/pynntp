# Round 0 review: PR #170 (fix/159-stray-yend, head 0fa3480)

Reviewer: hk-r0-haiku-a (Haiku 5.5, round 0, read-only). Base: upstream/main 2bfca17.
Scope: #159, a stray =yend after a complete yEnc block raised NNTPYEncError.
Net diff reviewed (not the commit series): the commits 47728a7 (XZVER feed-after-end) and its revert 0fa3480
cancel out; the net change is (a) XZVER/XZHDR `_info_yenczlib` ignores lines after the first =yend and raises
on a second =ybegin, (b) `_inflated_lines` helper (same logic as the old inline loop), (c) `_decode_yenc`
recognises =yend only while a block is open (nntp.py:1471-1474 at head, `elif open_block and ...`).
Method: read the head nntp/nntp.py (_info_yenczlib, _inflated_lines, _decode_yenc, _info_plain), nntp/yenc.py
check_trailer (head), base `_decode_yenc`, the test diffs. No code run here, no host run.

## Findings

### 1. Med: an early =yend inside an open block hides the real trailer; the body comes back empty with no error

- File: nntp/nntp.py:1471-1474 at head (`elif open_block and line.startswith(b"=yend"):`), together with the
  `if line[:2] != b"=y": if open_block: ... continue` branch at :1450-1453.
- Input (a broken, or hostile, server; BODY, ARTICLE, or any path that decodes yEnc through _decode_yenc):

      =ybegin line=128 size=4 name=x
      =yend size=0
      abcd
      =yend size=4 crc32=<crc of abcd>
      .

  (`=yend size=0` with no crc keyword, or `crc32=00000000`, passes check_trailer for the empty decode, since
  check_trailer requires size and checks crc only when present; yenc.py:76-100.)
- What goes wrong: the stray line closes the block (open_block = False). "abcd" is then dropped as text outside
  a block (:1464-1466), and the real =yend is ignored because `open_block` is False. The result is `b""` with
  no error: the client reports success for an article whose block says 4 bytes. The real trailer, the one
  that would have caught it, is never checked.
- Base (upstream/main) for the same input: `elif line.startswith(b"=yend")` has no open_block guard, so the
  real =yend is checked against size 0 and raises NNTPYEncError ("decoded 0 bytes, trailer says 4"). So this
  is a regression that the change introduces: a loud error becomes silent data loss.
- Triggered by: any server that sends an early =yend with size 0 (or a size matching the empty decode) in a
  block before its data. Not a valid yEnc stream. The harm is silent (empty body delivered as good). Rated
  Medium because it is a regression and loses data silently; a reader who counts only hostile servers would
  rate it Low (the server could deliver any body anyway).
- Confirmed by reading (the code path above, and check_trailer). Not run.
- New in the change (the `open_block and` guard). The test file does not cover a stray inside a block; the
  added tests cover only stray lines after a closed block (test_yenc_stray_trailer_outside_block,
  test_yenc_stray_trailer_between_blocks) and a bad block with a later stray.
- Suggested direction (for the lead, not written here): keep the first =yend of an open block as the trailer
  and check it, and only drop =yend lines when no block is open; a test with the input above that expects
  NNTPYEncError with data b"" would pin it.

## Checked by reading (no finding)

- XZVER/XZHDR, `_info_yenczlib` (head :536-577): after the first =yend, lines are not decoded or fed to inflate,
  so the size and CRC are computed over the data before the trailer only (check_trailer uses that size).
  A stray =yend after the trailer (the #159 case) is ignored, and a stray =yend before the data is caught:
  nothing is fed to inflate, so inflate.eof is False and the response raises "compressed data is truncated".
  Loud, not silent. Covered by test_xzver_early_yend_in_data.
- A second =ybegin after the trailer raises NNTPDataError after the terminator is read (`lines` is `_info_plain`,
  so the connection stays in sync; `_response` then marks it broken, nntp.py:609-612). Test present.
- `_inflated_lines` (head :524-534): the loop is the same as the old inline loop (`_inflate`, write, yield
  complete lines, stop when the output is shorter than _INFLATE_SIZE). Checked against base :540-548.
- Revert pair 47728a7 / 0fa3480: the net diff contains no change to the feed-after-end behaviour. Checked.
- Test helper `yenczlib(..., after=)` (tests/helpers.py): `after` is sent between the trailer and the
  terminator; only used by the new XZVER/XZHDR tests. Checked.
- `=yend` inside valid yEnc data cannot occur: '=' is an escape and "=y" is not a valid escape sequence, so
  the `line.startswith(b"=yend")` test cannot misfire on data.

## Notes (not findings)

- XZVER/XZHDR now silently ignore everything after the first =yend (except a second =ybegin). This is the
  intent of the change. A broken server could append junk after a valid trailer and it is accepted; the
  payload itself is still size- and CRC-checked, so no data is wrong.
- Pre-existing, not in this diff: in `_decode_yenc` a second =ybegin while a block is still open decodes the
  first block into the body and resets the trailer state without checking the first block (no =yend). The
  missing trailer is not reported (the "missing =yend trailer" error only fires for the last block). A
  broken server can truncate a first block silently. Same code on base; out of scope for #159.
- The test comments and the helper docstrings are accurate; the =yend-after-complete-block test names match
  their inputs.

## Did not check

- Real servers' yEnc output for XZVER (no network, no host run).
- Multipart posts with =ypart between blocks in the XZVER path (XZVER is single-part by design).
- Whether any caller depends on a stray =yend being an error (the docstring of _decode_yenc does not say).

## Score

6.5 / 10. The #159 fix works by reading (stray lines after a complete block are ignored, XZVER keeps the
connection in sync), but the `open_block` guard lets an early =yend hide the real trailer and return an empty
body with no error, where base raised. Fix finding 1 (with a test for the input above) before this goes further.
