# Council r2b: fix/yenc-unclosed-block @ 2cf7f35 (hk-council-opus-d, Claude Opus 5.5)

Base upstream/main 2bfca17. Commit reviewed: 2cf7f35 only. I reviewed by reading only, with no host run, so I make no claim that tests pass.

## What I checked
- The whole `_decode_yenc()` and `_read_body()` at the head (nntp/nntp.py:1398-1474): the state of `open_block`, `seen_block` and `error` across `=ybegin`, `=yend`, `=ypart`, text outside blocks, and the end of the response.
- New check at nntp/nntp.py:1456-1457: when a second `=ybegin` arrives while a block is open, the error is "missing =yend trailer" and the first error wins (`error or ...`). This matches the end-of-response check at :1468. The pending data is decoded first (`decode_pending()` at :1454), so block 1's bytes stay in `NNTPYEncError.data`. The decoder and size are then reset, so block 2 is still checked against its own trailer.
- The response is always read to its end (raising happens after the loop), so the connection stays in sync. The test confirms this with a follow-up DATE.
- Docstring (Raises: "a =ybegin has no =yend") already covers this case.
- Test `test_yenc_missing_trailer_before_next_block`: it checks the error, `data == first + second`, and sync. It fails on the base (lead's check), because there the two blocks decode cleanly with no error.

## Findings
None.

## Notes (not findings)
- Pre-existing, out of scope: a stray `=yend` with no open block is checked against the previous block's size and CRC. That only matters for broken posts and causes no harm.
- A behaviour change worth a line in the release notes: an unclosed block followed by another block now raises `NNTPYEncError` where it used to return data silently. The data is still in `.data`.

## Not checked
- No host run.
- Multipart (`=ypart`) bodies with an unclosed part, by test. By reading, the same path applies.

## Score
9.6. It is one concern, the change is minimal and correct, and it has a regression test that checks data and sync.
