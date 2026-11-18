# Council r2b: PR 6 fix/yenc-keyword-regex @ 54751e2 (reviewer hk-council-opus-e, Claude Opus 5.5)

Base upstream/main 2bfca17. Reviewed by reading only (`git diff upstream/main...54751e2`, full
nntp/yenc.py at head, call sites in nntp/nntp.py). No host run; I claim no test results.

## Findings

Nothing found.

## What I checked

- Equivalence: `(?<!\w)(\w+)=(\S*)` gives the same `findall` result as the old `(\w+)=(\S*)` on
  every input. An old match could only start mid-word if the earlier start in the same word failed;
  but `=` is not `\w`, so every start in one word run reaches the same end and fails or succeeds
  together. After a match, `\S*` stops at whitespace or end of line, so the next match starts after a
  non-word byte. Bytes pattern, so `\w` is ASCII only, as before.
- Linear time: inside a word run the fixed-width lookbehind fails in O(1); at each word start `\w+`
  runs to the end of the word once. Other shapes (`a-a-a-...`, `====`, `a=a=a=...`) are linear too.
  `split(b" name=", 1)` is linear. No other regex on yEnc lines (`_CRC32_RE`, `_DIGITS_RE` are
  fullmatch on short values; `_ESCAPE_RE` is linear).
- Input size: lines are bounded by max_line_length (64 KiB), so the old worst case was ~2e9 regex
  steps per line on `=ybegin` and again on `=yend`; reachable by any poster in body()/article().
- Tests: the table test pins the parsing (word-start keys, `a-b=c`, `x=1x=2`, `==4`, `a==5`, trailer
  keys); the timing test (65536-byte run, < 1 s) fails on the base; the article test checks the
  connection stays in sync with long runs on both `=ybegin` and `=yend` lines under the line limit.
- One concern; comment explains why the lookbehind is there; no CHANGELOG edit (CONTRIBUTING
  forbids it).

## Notes (not findings)

- The 1 s wall-clock bound is generous (linear work on 64 KiB is milliseconds), so CI flakiness is
  unlikely; a slow free-threaded runner is the only plausible risk.

## Not checked

- No host run (tests, timing on 3.14t/3.15t). Behaviour of `\w` under a future `re` change.

Score: 9.6
