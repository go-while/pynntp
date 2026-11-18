# Round 0 cross-check of the Haiku findings on #168-#172 (hk-r0-sonnet-a)

By reading at the PR heads only; nothing was run (G1). Files read: nntp/nntp.py (#170 head 0fa3480, #171 head c84dc8d), nntp/fifo.py, nntp/yenc.py `check_trailer`.

## 1. #170 early `=yend` closes the block, data dropped, real trailer ignored: CONFIRMED, new, Low

Code at the head (nntp.py:1464-1474): after `=ybegin`, `open_block` is True. A line `=yend size=0` goes to `check_trailer(line, size=0, crc32=0)`. That passes if the trailer says `size=0` and has no CRC or `crc32=00000000`, so `open_block` becomes False. The data lines that follow are dropped (`if open_block:` is False, same on base). The real `=yend size=N ...` is now skipped by `elif open_block and ...`. At the end `seen_block` is True, `open_block` False, `error` None, so `_decode_yenc` returns `b""` with no error.

Base: the same early trailer closes the block and the data is dropped the same way, but the real trailer was checked against size 0 and gave "decoded 0 bytes, trailer says N" (NNTPYEncError). So the silent empty result is new. It is the price of #159: a stray trailer after a complete block and an early trailer followed by data look the same to the loop.

Conditions: the early trailer must be consistent with what was decoded so far (size=0 with nothing decoded, or the exact size and CRC of a prefix); a wrong size still raises. A conforming encoder never produces this.

Can a valid encoder emit a data line starting with `=y`? No. In yEnc, `=` is followed by (critical byte + 64), where the byte is already shifted by +42. The critical bytes are NUL, LF, CR, `=` (and optionally TAB, SPACE, `.` at line start): the characters after `=` are `@ J M }` (and `I`, backtick, `n`). `y` would need the shifted byte 57 ('9'), which no encoder escapes. So `=yend`/`=ybegin` at line start cannot come from a conforming encoder; only from a broken one that escapes everything. Base treated `=y` lines as control lines for the same reason.

Who triggers it: a poster who builds such an article (any Usenet poster), or a server relaying/hostile. Harm: body returns empty or truncated without an error. A hostile server or poster can get the same effect on base and on any other decoder with a short block whose trailer is valid, so the check being lost here protects only against accidental damage that conforming encoders do not produce. I rate it Low, not Med (rule: hostile server Low unless it leaks credentials or corrupts data; here the data is cut, but the same cut is possible without the early trailer).

Cheap fix, if the lead wants it: count non-blank text lines dropped outside a block after a block was closed; a `=yend` that arrives with no open block after such lines is an error ("yEnc data outside a block"). The stray-trailer tests (trailer directly after the real trailer, or between two blocks) still pass; a signature followed by a stray `=yend` is not a normal article anyway.

Score: #170 8.5 -> 8 (adds a second Low finding to F1/F2).

## 2. #171 LF-only XZVER/XZHDR payload yielded as one merged row: CONFIRMED, I missed it, Low

`BytesFifo.readline()` splits on CRLF only (`_EOL = b"\r\n"`, fifo.py:25, 120-135). A decompressed payload with LF-only endings is never split, so everything stays in `buf`. Base: below `max_line_length` it was dropped silently (no rows, no error); at or above it, `_lines()` raised "Line longer than ...". Head (nntp.py:566-568): `yield last` returns the whole payload as one "row". `_xover` then does `rstrip("\r\n").split("\t")`: row 1 gets parsed with its later rows glued into the last field (`me\n2`), and `xzhdr` gives `(1, "hello\n2 world")`. So rows 2..n are lost inside field text, and the result looks plausible.

Who triggers it: a server or relay that sends bare LF in XZVER/XZHDR data (non-conforming; I know of no real one, commercial servers use CRLF), or a hostile server. Both before and after the change the outcome is silent wrong data (nothing vs garbled single row), so it is not a new class, but the garbled row is arguably worse than an empty list. My earlier report said a junk leftover "raises"; that holds for a lone `\r`, not for embedded LFs.

Suggested fix: yield the leftover only if it contains no `\n` (else raise NNTPDataError "Line without CRLF"). A genuine last row without any line ending has no `\n`, so the PR's tests still pass.

Score: #171 9.5 -> 9.

## 3. #169 id after other text gives True: CONFIRMED, stays a trade-off, Low

Code at the head (nntp.py:1812-1818): only `parts[0]`, or `parts[2]` after a leading `Article received`, is tried. `240 Article received ok <id>` gives parts `["Article","received","ok","<id>"]`, so after dropping the prefix `parts[0]` is `ok` and the result is True. Base returned the id (substring search). Silent, yes.

Who triggers it: any server whose 240 puts the id after other words. I do not know of one in the repo's notes (INN, Diablo, OUS, NewsCache, go-pugleaf are tested), so it is a possible regression with no known victim. Harm: the caller does not learn the server-visible id; the return type and docs already say the id is optional and non-standard, and callers normally posted their own Message-ID header. The pair of goals cannot both hold: accepting any `<...>` token anywhere is exactly the #156 bug (`report abuse to <abuse@example.net>`), so a narrower rule cannot recover this case without bringing the bug back. Keep as documented trade-off; suggest the PR text says "servers that put the id elsewhere now give True".

Score: #169 stays 9.

## Updated scores
#168: 9.5 (unchanged)
#169: 9 (unchanged), 0 findings, 1 Low trade-off
#170: 8, 3 findings (0/0/3): PR body omits the XZVER/XZHDR change; early =yend then data gives an empty body without error (new); pre-existing missing =yend before a later =ybegin unnoticed
#171: 9, 1 finding (0/0/1): LF-only payload yields one merged row
#172: 9 (unchanged), 1 finding (0/0/1)
