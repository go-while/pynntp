# Council r1: PR #170 (fix/159-stray-yend, head eb5c5aa), reviewer hk-council-opus-f

Base upstream/main 2bfca17. Reviewed: the net diff (47728a7 and its revert 0fa3480 cancel out, confirmed), `_info_yenczlib`,
`_inflated_lines`, `_read_body`, `_decode_yenc` and `nntp/yenc.py:check_trailer` at the head, `tests/helpers.py:yenczlib`,
and the new tests in test_articles.py and test_overview.py. By reading only; no host run.

Score: **9.0**

## Findings
None at Low or above. The decoding logic is right for every input I traced (see Checks).

## What keeps it below 9.5 (both quick to fix)
1. **The net diff carries a change that isn't part of the concern.** `_inflated_lines` (nntp.py:524-534, used once at :569)
   came from 395a512 to serve 47728a7. 47728a7 is reverted, so what is left is a behaviour-neutral refactor of the
   inflate loop that #159 doesn't need. Drop 395a512, or inline the loop again, so the PR is only the stray-`=yend` fix.
   This also makes the textual conflict with #171 smaller.
2. **The `_decode_yenc` docstring's Raises section misses the new error.** nntp.py:1445 still says "If yEnc data does not
   match its trailer, a =ybegin has no =yend, or there is no =ybegin". The head now also raises
   "=yend after data outside a block" (nntp.py:1480). Add "or a =yend follows text outside a block (an early =yend)". Also,
   the comment at nntp.py:1453 ("since it closed") and the docstring text at :1441 ("since the last block closed") don't
   match the code: `dropped` also counts text before the first block and is reset by every `=yend`, the stray ones too.
   Reword it as "since the last =yend (or the start of the body)".

## Checks
| Check | Result |
|---|---|
| One concern | Mostly: stray `=yend` in both yEnc readers (articles and XZVER/XZHDR). The second-`=ybegin` rejection follows from "the first `=yend` closes the XZ block". `_inflated_lines`: see item 1 above. |
| Fails on base, passes on head (by reading) | `test_yenc_stray_trailer_outside_block`: base checks the stray against the closed block (size mismatch, raises). `test_xz*_stray_yend_after_trailer`: base lets the stray replace `trailer`, so size=0 mismatches. `test_xz*_second_block_after_trailer`: base yEnc-decodes the `=ybegin` line into the finished inflater, which doesn't give the "second =ybegin" error. `test_xzver_early_yend_in_data[valid]`: base decodes all of it and succeeds; head raises "truncated" (stricter, see notes). `test_yenc_early_trailer_does_not_hide_data`: base checks the real trailer against size 0 and fails with "trailer says", not "outside a block". |
| Edge cases | Blank/whitespace-only lines between block and stray (ignored, test). Stray between two blocks (test). Bad block before a stray (`error = error or ...` keeps the first, test). Early `=yend` that validates (size=0) followed by data and the real trailer (error, test). Multipart pcrc32 (part=2 parametrised). Response read to its end on every error path (date() checks). XZ: data after the first trailer is ignored; completeness is still guaranteed by size/CRC of the first trailer plus `inflate.eof`. |
| Docstrings | `_info_yenczlib` matches. `_decode_yenc`: see item 2. |

## Notes (not findings)
- nntp.py:561-569: an XZ response with a `=yend` line in the middle of the data, followed by the rest and a correct final
  trailer, worked on base and now raises ("truncated" or a size mismatch). Only a broken server sends that: sane yEnc
  encoders never start a data line with `=y` (escapes map only to `@ J M }` and optionally `I ` n`). It fails loudly and
  matches the documented "only the first =yend is checked" rule.
- nntp.py:1478-1480: an identical duplicate trailer after text (`=yend…`, `-- sig`, the same `=yend…`) passed on base and
  now raises. That input is contrived; noted only for completeness.
- An early `=yend` that validates, with data after it and no later `=yend`, still drops that data silently. Base does the
  same, so this is pre-existing (it looks like a trailing signature).
- Process: #170 and #171 conflict textually in the `_info_yenczlib` docstring (`git merge-tree` reports a conflict in
  nntp/nntp.py). Whichever merges second needs a rebase. The code changes combine cleanly in meaning.

## Not checked
No host run. Not checked against real XZVER servers.
