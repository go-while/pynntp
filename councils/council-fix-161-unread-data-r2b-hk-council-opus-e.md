# Council r2b: PR 10 fix/161-unread-data @ 976d46e (reviewer hk-council-opus-e, Claude Opus 5.5)

Base upstream/main 2bfca17. Reviewed by reading only (diff of the 3 commits, nntp.py `_recv`,
`_decompress`, `_info_gzip`, `_info_yenczlib`, `_command`, `_transfer`, `compress`, `__exit__`
at head; tests/helpers.py, conftest.py and the new tests; issue #161 text). No host run; I claim
no test results.

## Findings

Nothing found.

## What I checked

- `_check_nothing_unread()` runs inside `_sync()` before every send in `_command` (so also before
  the AUTHINFO commands of a 480 retry, which the test pins) and before the article in
  `_transfer`; a raise there sends nothing and marks the connection broken. That matches #161's
  scope ("arriving in the same read") and its suggested fix.
- COMPRESS: pending inflate output (`_inflate_more`) is pulled once with `_decompress(b"")`; a
  sync-flush block inflates to nothing and is not data; a reply that fills `_INFLATE_SIZE` exactly
  is not a false positive; a stray line still inside the decompressor is found. All four tested. A
  corrupt block found here closes the connection, as before.
- gzip: `_info_gzip` puts what is left after the "." back in `_buffer`; with the check, that is
  now refused instead of being read as the next reply (dot-line, TERMINATOR and stray-inside-gzip
  cases tested, and gzip inside COMPRESS). XZVER leftover tested.
- No legitimate path leaves data in `_buffer` between commands: pynntp does not pipeline, the
  STARTTLS check was already stricter, and `compress()` inflates bytes behind the 206 before the
  next command.
- `__exit__`: with stray data, QUIT raises NNTPProtocolError, the socket is closed and the error
  raised if the block did not raise. On the base the stray line was QUIT's reply, so it raised (or
  hid) too; no regression.
- Test helper: `FakeSocket` now ends each recv at a reply end (`_reply_ends`), which models a real
  server and is needed so existing tests don't trip the check. A wrong mark only splits a recv; a
  missing one fails loudly. Its `_MULTILINE` set lacks 211 (LISTGROUP), which only adds a split,
  harmless. `Packets` gives exact recv boundaries for the new tests.
- Docstrings of NNTPSyncError, NNTPProtocolError and `command()` describe the new raise.

## Notes (not findings)

- Detection covers only data already received (same recv, or inflated by it). A stray reply that
  arrives in a later segment still becomes the next reply; the tests say so in comments, but the
  public NNTPProtocolError docstring ("finds data the server sent beyond the reply") does not. One
  word ("data already received beyond the reply") would set the right expectation. A non-blocking
  socket peek (plus `SSLSocket.pending()`) could widen it later; out of #161's scope.
- In `_info_gzip` TERMINATOR mode, inflate output produced after the "." in the `while not
  inflate.eof` loop is dropped, not put back in the buffer, so a stray line there is silently
  ignored rather than refused. Pre-existing and harmless (nothing is shifted).

## Not checked

- No host run; real servers' behaviour with XFEATURE COMPRESS GZIP TERMINATOR (whether any send
  a plain "." after the gzip stream as well; if so this PR raises at the next command, where the
  base misread the "." as a status line and also raised).

Score: 9.5
