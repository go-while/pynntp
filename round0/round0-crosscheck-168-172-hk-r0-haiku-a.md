# Round-0 cross-check of Sonnet's findings on #168-#172 (hk-r0-haiku-a)

Method: read the heads again (nntp/nntp.py, nntp/utils.py, tests), read the PR bodies with gh pr view
(read-only), fetched origin/fix/yenc-unclosed-block (PR #178) for the diff only. No code run, no host run,
no edits.

## 1. #170 F1 (Low): PR body and tests cover only the article path; head also changes XZVER/XZHDR

CONFIRMED. The head changes `_info_yenczlib` (nntp.py ~536-577): lines after the first =yend are no longer
decoded (`if trailer: ... continue`), and a second =ybegin after the trailer raises NNTPDataError ("second
=ybegin after the trailer"). The PR body (gh pr view 170) describes only `_decode_yenc()` and the BODY/ARTICLE
tests. The XZVER/XZHDR tests (test_overview.py: test_xzver_stray_yend_after_trailer, test_xzhdr_*,
test_xzver_second_block_after_trailer, test_xzver_early_yend_in_data) are not mentioned.
Who triggers: nothing new at runtime; this is a scope and review-process gap. The brief asks for one concern
per change; this PR has two code paths (yEnc body decode and XZVER/XZHDR). The body should say so, or the
XZVER part should go in its own PR.
Score effect: none on its own. My finding 1 (Med) below still stands and the body path is where it lives.

## 2. #170 F2 (Low, pre-existing): a =ybegin while a block is still open

CONFIRMED as pre-existing, and it belongs in #178, not #170. At the #170 head, nntp.py:1468-1470 is
`if line.startswith(b"=ybegin "): decoder, size, open_block, seen_block = YEnc(), 0, True, True`, with no
check of the block that is still open. The earlier block's data is already in `body` (decode_pending), and no
trailer check runs for it. Base has the same code, and #170 does not change this branch (its net diff only
adds `open_block and` to the =yend branch at :1471). Triggered by a broken or hostile server that sends
=ybegin, data, =ybegin without =yend. The first block is returned without error.
#178 (fix/yenc-unclosed-block, nntp.py +2 lines at ~1455) adds exactly that check
(`if open_block: error = error or "missing =yend trailer"`). Agree: it belongs in #178.
Score effect: none for #170. Note that #178's check does not touch the early-=yend case in my finding 1.

## 3. #172 F1 (Low): wall-clock 3 s limit in test_parse_headers_many_continuation_lines

CONFIRMED. tests/test_utils.py asserts `elapsed < limit` with `limit = 3.0` seconds for 500,000 continuation
lines. The code is linear, so the test is about the host's speed; on a loaded or slow CI runner it can fail
without any defect. Who triggers: nobody at runtime; it is a flaky test in the PR.
Score effect: yes, -0.5. A flaky test shipped in the PR is a defect of the PR. Suggest a count-based check
(e.g. compare two sizes) or drop the timing assert.

## 4. #168 (note): PR body covers only reconnect(); head also changes close()

CONFIRMED. The PR body (gh pr view 168) describes `_response()`, `_info()` and `reconnect()`, and the tests
named there. The head also changes close() (nntp.py:790-799): it sets `_reading = False` and swaps in a new
BytesFifo, and the close() / with-exit tests (test_iterator_resumed_after_close_raises,
test_command_after_close_with_open_iterator) are not in the body. I read this change and found it correct
(see round0-pr168-hk-r0-haiku-a.md). Who triggers: nothing new; the body is incomplete.
Score effect: none. Body should name close() and the with-exit path.

## Updated score lines

#168: 9.5, 0 findings (H/M/L: 0/0/0): - (body should also cover close(), not a code defect)
#169: 8.5, 1 findings (H/M/L: 0/0/1): an id not in the first reply position is no longer returned (silent True)
#170: 6.5, 1 findings (H/M/L: 0/1/0): an early =yend inside an open yEnc block hides the real trailer and returns an empty body silently; scope: body misses the XZVER/XZHDR change (split or update body); pre-existing =ybegin-while-open belongs in #178
#171: 8.5, 1 findings (H/M/L: 0/0/1): an LF-only XZVER/XZHDR payload is merged into one bogus row
#172: 9.0, 0 findings (H/M/L: 0/0/0): - (flaky 3 s wall-clock assert in the new test; was 9.5)
