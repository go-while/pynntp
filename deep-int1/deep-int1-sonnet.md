# deep-int1 review by hk-deep-sonnet (Sonnet 5.5)

Head e07f041 (integration-1), base 2bfca17 (3.3.0). Read completely: nntp/nntp.py (2146 lines), utils.py,
yenc.py, headerdict.py, fifo.py, types.py, __init__.py. Also read: .github/workflows/*, tests/conftest.py,
tests/helpers.py, tests/faults/{conftest,test_faults,README}.py, the harness half of tests/faults/scenarios.py
(lines 2380-2725) and the xzver/yenc scenario tables, the header of tests/integration/inn2/test_inn2.py and setup.sh.
One run on a test host (job 999, a test host) to confirm finding 1; the probe folder is removed.

## Findings (ordered by severity)

### 1. Med: a "COMPRESS=GZIP" substring anywhere in a status line, including the Message-ID the server echoes, selects gzip decoding

- Where: nntp/nntp.py:677 (`if "COMPRESS=GZIP" in message:` in `_info()`); also `info()`/`_unexpected()` use `_info()`.
- Trigger: any article whose Message-ID contains the text `COMPRESS=GZIP` (valid message-id characters: letters, "=",
  "-"), e.g. `<x-COMPRESS=GZIP@evil.example>`. Servers echo the id in the 220/221/222 status line
  (`220 5 <x-COMPRESS=GZIP@evil.example> ...`). `article()`, `head()` and `body()` then run `_info_gzip()` on a plain
  response, `zlib.error: incorrect header check`, `NNTPDataError("Decompression failed")`, connection marked broken.
  It fails the same way on every retry, so the article can never be read with pynntp, by number or by message-id.
- New or old: pre-existing in 3.3.0 (same line in base).
- Confirmed by a run (test host, head e07f041): `client.article(5)` against
  `220 5 <a-COMPRESS=GZIP@x> article follows\r\nSubject: hi\r\n\r\nbody\r\n.\r\n` raises NNTPDataError
  (`Decompression failed`, `zlib.error ... incorrect header check`); `body("<COMPRESS=GZIP@x>")` raises NNTPDataError and
  the next command raises NNTPSyncError. Quotes: nntp.py:677-680.
- harm: DoS per article (an article that can't be fetched, and a broken connection each time; a caller that retries
  on NNTPDataError with reconnect loops forever on it).
- who can trigger it: anyone who can post an article with a chosen Message-ID (Usenet poster, or a feed peer); the
  server is honest.
- crash: none (an exception in the caller's process; one user per fetch of that article, every client that fetches it).
- exploit: DoS only, shown.
- conditions: default config; no XFEATURE needed (the check runs even if gzip was never negotiated); case-sensitive match.
- verdict: fix soon. Make the marker count only when xfeature_compress_gzip() was issued (a client flag, reset in
  `_connect`), and not for 22x article replies; or require the marker as a bracketed last token.

### 2. Low: ssl_context / ssl_mode silently ignored without use_ssl=True, so a connection the caller thinks is TLS is plain text and credentials go in clear

- Where: nntp/nntp.py:363-375 (`if use_ssl:` only then `SSLMode(ssl_mode)`), nntp.py:391, 398 (both TLS branches need `_use_ssl`).
- Trigger: `NNTPClient(host, ssl_context=ctx)` or `NNTPClient(host, ssl_mode=SSLMode.STARTTLS, username=..., password=...)`
  without use_ssl: no TLS, no error, AUTHINFO sent in clear on 480. Same with `from_url("nntp://...", ssl_context=ctx)`.
- New or old: pre-existing; the docstrings (nntp.py:349, 352, 1004) say it is ignored, so it is documented.
- Confirmed by reading.
- harm: leak (credentials in clear text) after a caller mistake that fails silently.
- who can trigger it: the caller; the on-path observer gets the benefit.
- crash: none. exploit: data integrity/confidentiality, theoretical (needs a caller mistake).
- conditions: option combination only.
- verdict: issue list only (docs are accurate). A ValueError when ssl_context is set or ssl_mode is not the default
  without use_ssl would make it fail closed; breaking change for callers who pass them harmlessly.

## Notes (not findings)

- An empty gzip response: `215 ... COMPRESS=GZIP` followed directly by `.\r\n` (no gzip stream) raises NNTPDataError
  (run: `incorrect header check`, nntp.py:584). I do not know whether a real server sends an empty result that way; if
  one does, every empty LIST/XOVER on it fails.
- `_MULTILINE` (nntp.py:136) lacks 202. `list("EXTENSIONS")` with the default `success=(215,)` gets 202 with a block;
  `_unexpected()` does not drain it, so the connection is not marked and the block is taken for the next reply unless
  already received (then NNTPProtocolError). Caller mistake; list_extensions() passes 202 and is fine.
- `_select()` (nntp.py:1544) and `ihave()` accept only RFC 3977 message-ids (`<`, 1-248 chars, no ">"). A real
  article with a longer or odd id makes STAT/NEXT/LAST raise NNTPDataError although the reply was valid (in sync, no loss).
  Also `article()` raises NNTPDataError after reading the whole article if the 220 line has no article number.
- `HeaderDict`/`parse_headers`: repeated headers (Received, Path-like) keep only the last value (documented).
- `parse_overview_fmt()` is strict; one odd line in LIST OVERVIEW.FMT makes xover()/over() unusable on that server
  (NNTPDataError from `overview_fmt`). Duplicate field names collapse silently in `_from_fields` (hostile server only).
- `head()` (`list(...)`), `help()` and `body()` buffer the whole response: an endless response from a hostile server
  grows memory without bound (Low by the rules; per-line cost is bounded by max_line_length).
- Servers that end lines with a bare LF (non-compliant) hang until the timeout: BytesFifo splits on CRLF only.
- `overview_fmt`/`_overview_fields` is cached for the instance, also across reconnect(); a 5xx on LIST OVERVIEW.FMT
  (e.g. 502 before login) caches the RFC 2980 default permanently.
- yEnc `=` immediately before a CRLF consumes the CR as the escaped byte (yenc.py:35); no standard encoder emits it.
- tests/faults/README.md "Known failures" table (#157, #159, #160, #161, #162 as open) is stale: in scenarios.py only
  `xzver/sync-flushed-not-finished` still has a known reason. Doc only.
- tests/faults is opt-in (collect_ignore without PYNNTP_FAULT_SERVER) and its workflow runs only on dispatch/weekly, so
  PRs are not gated by it (as designed). nntp-testkit is pinned by tag (v0.14.1), not by commit; `greenbender/inn` in
  check.yml is an unpinned image. check.yml runs `sudo tests/integration/inn2/setup.sh` from the PR's own checkout on
  `pull_request` (no secrets, read-only token for forks, ephemeral runner): acceptable. The default-run integration
  tests skip TLS verification without PYNNTP_TLS_CAFILE, but `test_tls_verifies_certificate_by_default` covers the default.
- Timing tests: test_utils.py:159 (10 s limit vs 20 s quadratic) and test_yenc.py:116 (1 s for 64 KiB; the quadratic
  case would be several seconds) have margin; low flake risk on free-threaded 3.14t/3.15t.

## What I checked and found sound

Response state machine (`_response`, `_reading`, `_broken`, `_sync`, close/reconnect with stale iterators, abandoned
and never-started iterators), `_command` 480 retry rules (AUTHINFO/MODE READER/STARTTLS/COMPRESS exclusions, no
credentials in messages), STARTTLS (no plaintext fallback, no login before TLS, buffer check), default TLS context,
COMPRESS DEFLATE (pending data after 206, `_inflate_more`, unused_data, output capped per call, line length checks),
`_info_gzip` (terminator after and inside the stream, `more`/eof/unused_data ordering, leftover handed back),
`_info_yenczlib`, `_decode_yenc`/`_stray_yend_error`/`check_trailer`, `YEnc.decode`, BytesFifo (queued writes, split
CRLF, invariant of `_eol_queued`), `_transfer`/`_prepare_article` (dot-stuffing, CR/NUL, header injection checks),
`_timestamp`, `from_url`, HeaderDict, utils parsers. No second bug found in these.

## Not checked

Most of tests/ (test_*.py bodies beyond samples), tests/faults/scenarios.py scenario bodies (only harness and the
xzver/yenc tables read), test_inn2.py beyond its header and TLS tests, docs/README text, real-server behavior
(no network access), free-threaded builds, Windows. No fuzzing; reading plus one run.

## Score: 8/10

What keeps it from 10: finding 1 (a poster-controlled string flips the response decoder, pre-existing) and the silent
plaintext on mismatched TLS options (documented design); the notes show some strict-parsing edges that turn valid
server replies into NNTPDataError.

deep-int1: 8, 2 findings (0/1/1): "COMPRESS=GZIP" in status line/Message-ID breaks article fetch (Med); ssl_context/ssl_mode ignored without use_ssl gives silent plaintext (Low)
