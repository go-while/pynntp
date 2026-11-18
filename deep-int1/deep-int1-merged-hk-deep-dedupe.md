# deep-int1 merged findings (hk-deep-dedupe, 2026-11-17)

Head e07f041 (integration-1) = upstream/main 2bfca17 (3.3.0) + 23 open PRs.
Sources: deep-int1-terra-oneshot.md (T), deep-int1-sol-oneshot.md (L),
deep-int1-sonnet.md (S), deep-int1-haiku.md (H). Checked against the brief's
known issues, TASKS.md, upstream-gap/deep-fixes-status.md ("2026-11-16 triage")
and the "Low impact, not fixed" / "Noted, not fixed yet" lists in
drafts/issue-166.template.md (called "#166 list" below).

Run: one test file, 10 probes (9 of them x3 recv chunk sizes = 28 cases), on a
test host via vm-run.sh (job 1003, 10.10.11.119), copy of the head in
/claude/trees/pynntp/hk-deep-dedupe (removed after): **28 passed**, i.e. every
behaviour marked "run" below reproduces at e07f041. Nothing ran on this machine.

## Raw findings (all four)

| Src | Finding | Their sev |
|---|---|---|
| S1 | "COMPRESS=GZIP" in a status line (echoed Message-ID) selects gzip | Med |
| S2 | ssl_context/ssl_mode ignored without use_ssl: plain text | Low |
| H1 | LF-only row merged with next CRLF row (XZ and plain) | Med |
| H2 | from_url error text can hold the password (NFKC netloc) | Low |
| H3 | >4300-digit numbers raise raw ValueError | Low |
| H4 | header names starting with "." not dot-stuffed | Low |
| T1 | =ybegin size not checked: silent truncation | Med |
| T2 | overview format cached across reconnect | Med |
| T3 | HEAD buffers the lines after the blank line (new) | Low |
| T4 | yEnc trailer size >4300 digits: raw ValueError | Low |
| T5 | integration test capability match is case-sensitive | Low |
| L1 | header names not dot-stuffed | Med |
| L2 | overview format cached across reconnect | Med |
| L3 | XZ: bytes after the end of the DEFLATE stream ignored | Med |
| L4 | mixed LF/CRLF XZ rows merged | Med |
| L5 | >4300-digit numbers raise raw ValueError | Low |

## Merged table

| ID | Title | Found by | New (PR) or pre-existing | Sev | Verdict | Verified how |
|---|---|---|---|---|---|---|
| M1 | "COMPRESS=GZIP" substring in a status line (poster's Message-ID) selects gzip | S | pre-existing 3.3.0 | Low (S: Med) | issue list only (decided 11-16, stays) | read nntp.py:677 + run |
| M2 | Mixed LF/CRLF rows merged into one row, next row lost (XZHDR/XZVER and plain XHDR/XOVER) | H, L | pre-existing; #171's comment claims it is refused but only the tail is checked | Low | fix in #171 now (narrow its comment/docstring); mixed case to issue list | read nntp.py:508-515, 655-664 + run |
| M3 | Header name starting with "." not dot-stuffed in POST/IHAVE | H, L | pre-existing | Low (L: Med) | issue list only (already on #166 list) | read nntp.py:2135, utils.py:30 + run |
| M4 | overview format cached across reconnect() | T, L, S(note) | pre-existing | Low (T, L: Med) | issue list only (already "Noted" on #166 list) | read nntp.py:1841-1849 + run |
| M5 | >4300-digit yEnc size= / STAT number: raw ValueError (yEnc case: next command NNTPSyncError) | H, T, L | pre-existing | Low | issue list only (decided 11-16, T3 dropped) | read yenc.py:93, nntp.py:1547 + run |
| M6 | =ybegin size never compared with the decoded size | T | pre-existing | Low (T: Med) | issue list only (new entry) | read nntp.py:1570-1645 + run |
| M7 | XZ: data after the end of the DEFLATE stream silently ignored (second stream dropped; unused_data grows) | L | pre-existing; #145 pins "accepted (observed)" | Low (L: Med) | issue list only (already on #166 list) | read nntp.py:229, 638-664 + run |
| M8 | head() buffers the whole response incl. lines after the blank line | T, S(note) | new in #185 | Low | issue list only (design limit on #166 list) | read nntp.py:1722-1726, git diff #185 |
| M9 | from_url(): urlsplit ValueError for an NFKC netloc quotes the whole netloc incl. password | H | pre-existing | Low | issue list only (already on #166 list); docstring overclaims | read nntp.py:1015-1018 + CPython _checknetloc + run |
| M10 | ssl_context/ssl_mode ignored without use_ssl=True | S | pre-existing, documented | Low | noise (documented; decided in council 11-16) | read nntp.py:349-375 |
| M11 | test_inn2 require()/offers_login() compare capability tokens case-sensitively | T | pre-existing pattern (base require() too); #167 rewrote it | Low, test-only | noise / issue list only | read test_inn2.py:124-170, base, git diff #167 |

No High or Med item survives verification. Nothing from the four reports is
refuted on the facts; the disagreements are about severity and about items
that were already decided.

## Per-item verification

### M1 "COMPRESS=GZIP" in a status line selects gzip (S1)

```python
# nntp/nntp.py:677
if "COMPRESS=GZIP" in message:
    lines = self._info_gzip()
```
Also used by `_unexpected()` (docstring nntp.py:735). Same line in 3.3.0
(upstream/main nntp.py:578). `_MESSAGE_ID_RE` allows "=", and 220/221/222
status lines echo the id.
Run: `body("<x-COMPRESS=GZIP@e.example>")` against
`222 0 <x-COMPRESS=GZIP@e.example>\r\nhello\r\n.\r\n` raises NNTPDataError
"Decompression failed"; the next `date()` raises NNTPSyncError. Confirmed.

- harm: wrong reply/DoS for one article: it can't be read with pynntp (also not with decode=False), and each try costs a reconnect.
- who: anyone who can post an article with a chosen Message-ID (or a feed peer); the server is honest.
- crash: none; an NNTPError in the caller.
- exploit: DoS only, shown (Sonnet's run, this run, and the T2 branch on 11-14 with 21 tests failing before).
- conditions: default config; no XFEATURE needed.
- severity: Low (Sonnet: Med). No corruption, no leak, recoverable by reconnect; the attacker gains the loss of one article for pynntp readers.
- verdict: issue list only.

**Does the new evidence change the 11-16 decision?** No. The run shows
nothing that was not known at triage: the 11-14 task spec T2
(tasks/deep-fixes.md) already describes exactly this vector ("a poster's
Message-ID `<COMPRESS=GZIP@x>` makes article()/body() feed a plain body to
gzip"), the #166 list carries it word for word, and the T2 branch (bb7639d)
already showed it on a host. So the triage weighed this exact trigger. One
point for the lead: the trigger is any poster, with an honest server and the
default config, not a hostile server, so it is "deliberately crafted input",
not "unlikely". If the lead reopens it, there is a fix that avoids T2's
behaviour change (raw `command("XFEATURE COMPRESS GZIP")` would stop enabling
gzip): treat the marker only as the last token of the status message, after
stripping `[]()` (nntp-testkit sends `(COMPRESS=GZIP)`, the tests use a bare
`COMPRESS=GZIP`), and keep the XFEATURE flag out of it. A Message-ID token
keeps its `<...>`, so it never matches.

### M2 Mixed LF/CRLF rows merged (H1, L4)

```python
# nntp/nntp.py:508-511 (_lines); BytesFifo.readline() splits on CRLF only (fifo.py:191)
while line := buf.readline():
    ...
    yield line
# nntp/nntp.py:659-664
# A finished stream may end without CRLF; do not lose its last row.
# Rows separated by a bare LF are not one row: refuse them.
if last := buf.read():
    if b"\n" in last:
        raise NNTPDataError("Bad XZ data: line ends without CRLF")
    yield last
```
The check only sees the tail after the last CRLF. Run: an XZHDR payload
`1 one\n2 two\r\n` gives `[(1, "one\n2 two")]`, no error, next DATE fine; the
same bytes as a plain XHDR reply give the same result. Confirmed.
The plain-response merge and the XZ merge are in 3.3.0. #171 (8ac5794
"refuse a bare-LF payload instead of one merged row") added the tail check;
its own test only covers LF rows after the last CRLF
(tests/test_overview.py:161-174), so its comment (nntp.py:660) and the docstring (nntp.py:626-627)
claim more than the code does.

- harm: silent row loss and a wrong value (the next row ends up in a field).
- who: a buggy or hostile server (RFC 3977 forbids LF in overview/HDR data).
- crash: none. exploit: data integrity, shown by a run.
- conditions: default config; any recv timing.
- severity: Low (hostile/buggy server, no credentials).
- PR: #171 (claim); behaviour pre-existing.
- verdict: fix in #171 now as docs: say the check covers an LF-only tail (and the commit/PR text), no code change, no new council round needed for a Low. The mixed-row case goes on the issue list. If code is preferred instead: in `_info_yenczlib` refuse a yielded line with `b"\n" in line[:-2]` (XZ only, so the plain loop's per-line cost is unchanged).

### M3 Header name starting with "." not dot-stuffed (H4, L1)

```python
# nntp/nntp.py:2135-2138
article.write(hdrs.encode(self.encoding, self.errors))
for line in lines:
    if line.startswith(b"."):
        line = b"." + line
# nntp/utils.py:30
_HEADER_NAME_RE = re.compile(r"[!-9;-~]+")
```
Run: `post({".X-Test": "v", "Subject": "hi"}, b"x\n")` sends
`POST\r\n.X-Test: v\r\n...`; a server unstuffs it to `X-Test`. Confirmed,
pre-existing (same code in 3.3.0, nntp.py:1898).

- harm: data change (one header name loses its leading dot).
- who: the caller, with a header name no real software uses.
- crash: none. exploit: data integrity, shown.
- conditions: default config.
- severity: Low (Sol: Med). Rare caller input; already on the #166 list ("a header name starting with `.` ... the server reads it as `X-Foo`").
- verdict: issue list only (decided).

### M4 overview format cached across reconnect() (T2, L2, S note)

```python
# nntp/nntp.py:1841-1843
@cached_property
def _overview_fields(self) -> tuple[tuple[str, bool], ...]:
    try:
        return tuple(self.list_overview_fmt())
```
`_connect()`/`reconnect()` (nntp.py:377-427) do not clear it. Run: after
`reconnect()`, `xover()` sends no `LIST OVERVIEW.FMT` on the new connection
and uses the old names. Confirmed, pre-existing (3.3.0 nntp.py:1629).
Harm needs the server's format to change between two connections of one
client. RFC 3977 8.4 fixes the order of the first seven fields, so only the
optional extra fields (after `:lines`) can move.

- harm: wrong field names on optional overview fields.
- who: the server operator changing the format, or a pool of backends with different formats behind one name.
- crash: none. exploit: data integrity, theoretical.
- conditions: the format changes during the client's lifetime, then reconnect().
- severity: Low (Terra, Sol: Med).
- verdict: issue list only (already "Noted, not fixed yet" on the #166 list: "the cached format is not reset by reconnect()"). Cheap fix if wanted: `self.__dict__.pop("_overview_fields", None)` in `_connect()`.

### M5 >4300-digit numbers raise raw ValueError (H3, T4, L5)

```python
# nntp/yenc.py:91-93
if not _DIGITS_RE.fullmatch(expected_size):
    return "trailer has no valid size"
if int(expected_size) != size:
# nntp/nntp.py:1547
return int(parts[0]), parts[1]
```
Run: a BODY with `=yend size=` + 4301 digits raises exactly `ValueError` (not
an NNTPError) and the next `date()` raises NNTPSyncError; a 223 reply with a
4301-digit number makes `stat()` raise `ValueError` (connection in sync).
Confirmed, pre-existing.
The yEnc case is reachable by a poster (the trailer is article content), not
only a hostile server.

- harm: wrong exception type; after body() the connection must be reconnected.
- who: a poster (yEnc trailer) or the server (STAT/NEXT/LAST).
- crash: the caller's task if it catches only NNTPError.
- exploit: DoS only, shown.
- conditions: CPython's default int_max_str_digits (4300).
- severity: Low.
- verdict: issue list only (decided 11-16: T3 "huge-numbers" dropped; on the #166 list).

### M6 =ybegin size never checked (T1)

```python
# nntp/nntp.py:1619-1631 (_decode_yenc)
if line.startswith(b"=ybegin "):
    ...
    decoder, size, open_block, seen_block = YEnc(), 0, True, True
    multipart = "part" in parse_keywords(line)
elif line.startswith(b"=yend"):
    if open_block:
        mismatch = check_trailer(line, size, decoder.crc32, part=multipart)
```
The `size=` of `=ybegin` is never read. Run: a BODY of
`=ybegin line=128 size=1 name=x`, `=yend size=0`, one data line returns `b""`
with no error; next DATE fine. Confirmed, pre-existing (3.3.0 has the same
logic). The data line after `=yend` is dropped as "text outside a block", as
the docstring says for signatures.
The trailer is self-consistent; only a crafted article (or an encoder bug that
writes a wrong but matching `=yend` early) gets here. A poster can put any
bytes in an article anyway, so the "true" payload is not defined.

- harm: an empty/short result without an error for a crafted article.
- who: a poster crafting the article.
- crash: none. exploit: data integrity, theoretical (no realistic corruption produces it).
- conditions: default yEnc detection, single-part block.
- severity: Low (Terra: Med).
- verdict: issue list only (new entry: "single-part =ybegin size= is not compared with the decoded size"). Fix idea if wanted: for a block without `part=`, add a mismatch when `=ybegin size=` differs from the decoded size.

### M7 XZ: data after the end of the DEFLATE stream ignored (L3)

```python
# nntp/nntp.py:229
return inflate.decompress(inflate.unconsumed_tail + data, _INFLATE_SIZE)
# nntp/nntp.py:656-658
if not inflate.eof:
    raise NNTPDataError("Decompression failed: compressed data is truncated")
```
`inflate.unused_data` is never checked. Run: an XZHDR block holding two
finished DEFLATE streams (`1 one\r\n`, `2 two\r\n`) with a correct yEnc size
and CRC returns `[(1, "one")]`, no error. Confirmed, pre-existing.
tests/faults/scenarios.py:1615-1622 (#145) has "data-after-deflate-end"
expecting success with the comment "Junk after the end of the DEFLATE stream
is accepted (observed)": it records today's behaviour on purpose; not a test
that can't fail.

- harm: silent loss of rows after the first stream; memory grows with the junk (unused_data concatenation, quadratic CPU).
- who: a buggy or hostile server.
- crash: none for finite input. exploit: data integrity/DoS, shown (loss).
- conditions: XZVER/XZHDR only.
- severity: Low.
- verdict: issue list only. Same root cause as the #166 entry "XZVER/XZHDR keep feeding data after the end of the zlib stream" (T10, reverted on #170 on 11-16); add "the data is also dropped silently" to that entry.

### M8 head() buffers the whole response (T3, S note)

```python
# nntp/nntp.py:1722-1726
# Read the whole response before parsing: parse_headers() stops at a
# blank or bad line, and the rest must not be left unread. HEAD is small.
lines = list(self._info(code, message))
with self._data_errors("article headers"):
    return utils.parse_headers(self._decode(iter(lines)))
```
New in #185 (b8e3bda). 3.3.0 already buffered every header line without a
cap (parse_headers), and body() returns the whole body by design. So a
hostile server gains nothing new; only lines after a blank line are now kept.

- harm: memory without bound from an endless HEAD reply.
- who: a hostile server.
- crash: the client process at OOM. exploit: DoS, theoretical.
- conditions: default config.
- severity: Low.
- PR: #185.
- verdict: issue list only (#166 list: "Design limits: no cap on the total size of body()/article()/head()"). Fix idea: parse from the iterator and then drain it (`for _ in lines: pass`), as article() does in the same PR.

### M9 from_url(): the NFKC ValueError holds the password (H2)

```python
# nntp/nntp.py:1015-1018
#     host, or a bad port, timeout or reader value. The message never
#     includes the URL, which may hold a password.
parts = urllib.parse.urlsplit(url)
```
CPython's `_checknetloc` raises `ValueError("netloc '" + netloc + "' contains
invalid characters under NFKC normalization")`. Run:
`from_url("nntps://user:s3cretpw＠x@example.com")` raises ValueError whose
text contains `s3cretpw` (no connection attempted). Confirmed, pre-existing
(urlsplit and the docstring promise are both in 3.3.0, nntp.py:871-873).

- harm: leak of the caller's own password into an exception text/log.
- who: the caller, with a password holding a full-width `@ / ? # :` (or U+2100-like) character.
- crash: none. exploit: leak, shown; needs that rare password.
- conditions: from_url() only.
- severity: Low.
- verdict: issue list only (on the #166 list: "from_url(): some error messages can contain parts of the password (... full-width characters)"; T12 from-url dropped 11-16). The docstring's "never includes the URL" is wrong for this case; a fix (`except ValueError: raise ValueError("Invalid NNTP URL") from None` around urlsplit) is 3 lines if the lead wants it.

### M10 ssl_context/ssl_mode ignored without use_ssl (S2)

```python
# nntp/nntp.py:349, 352
use_ssl: Use TLS. ssl_mode and ssl_context only take effect with it.
...  Ignored without use_ssl=True.
# nntp/nntp.py:363-365
if use_ssl:
    # A misspelt mode used to take neither TLS branch: plain text
    ssl_mode = SSLMode(ssl_mode)
```
Confirmed by reading; documented. Council r1 on 2026-11-16 dropped the
refusals (breaking config/env use) and kept only the SSLMode validation.

- harm: password in clear after a caller mistake; documented.
- who: the caller. crash: none. exploit: leak, theoretical.
- severity: Low. verdict: noise (decided, documented).

### M11 integration-test capability match is case-sensitive (T5)

```python
# tests/integration/inn2/test_inn2.py:127, 166
words[:1] == ["AUTHINFO"] and "USER" in words
if words[:1] == [name] and all(keyword in words for keyword in keywords):
```
Confirmed by reading. 3.3.0's `require()` was case-sensitive too
(`f"{line} ".startswith(f"{capability} ")`); #167 rewrote it and added
`offers_login()` the same way. INN and every server we know send upper case;
a lower-case server would only make some optional tests skip.

- harm: test-only (a skipped optional test). who: an integration server with lower-case capabilities, none known.
- severity: Low. verdict: noise / issue list only. Fix idea: compare `word.upper()`.

## Notes (not findings)

- Empty gzip result (`... COMPRESS=GZIP` then `.` with no gzip stream) raises NNTPDataError (S note): unknown whether any server sends that.
- 202 missing from `_MULTILINE` (S note): decided 11-16 (T4 dropped), on the #166 list.
- `_select()`/`ihave()` accept only RFC 3977 message-ids; `article()` raises after reading if the 220 line has no number (S note): in sync, no loss.
- A server ending lines with bare LF only hangs until the timeout (S note): non-compliant server.
- A 5xx to LIST OVERVIEW.FMT before login caches the RFC 2980 default for the client's life (S note): part of M4.
- yEnc `=` right before CRLF eats the CR (S note): no encoder emits it.
- tests/faults/README.md status of #157/#159-#162: correct for #145 on its own (those bugs are open on upstream/main); stale only on integration-1, where the fixes are merged. Update when the fixes land.
- Haiku N1-N10 and Sol's notes: no further item.

## Lists

Fix in a PR now:
- M2: #171, narrow the comment at nntp.py:659-660, the `_info_yenczlib` docstring and the PR/commit text to "an LF-only tail" (docs, no code). Optional code variant above.

Issue list (#166 "Low impact, not fixed" / "Noted"):
- already there, no change: M1 (decision stands), M3, M4, M5, M8 (design limits), M9.
- extend: M7 (add "the data after the stream is dropped silently").
- new: M2 mixed LF/CRLF rows (plain and XZ), M6 single-part =ybegin size not checked.

Refuted / noise:
- none refuted on the facts.
- noise: M10 (documented, decided 11-16), M11 (test-only, no known server).

Score view: no High or Med finding at e07f041; the four reports' Med ratings
(S1, H1, T1, T2, L1-L4) drop to Low under the findings rule (hostile/buggy
server or a rare caller input, no leak or corruption of real data), and most
of them were triaged on 2026-11-16.
