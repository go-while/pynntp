# Council r2b: PR 8 fix/head-read-all @ edbe199 (reviewer hk-council-opus-e, Claude Opus 5.5)

Base upstream/main 2bfca17. Reviewed by reading only (diff, nntp.py `_info`/`_response`/
`_data_errors`/`_sync`/`article`/`head`/`_read_body` at head, `utils.parse_headers`). No host run;
I claim no test results.

## Findings

Nothing found.

## What I checked

- Base behaviour: `head()` gave `parse_headers()` the live iterator; at a blank line inside the HEAD
  response it returned early, the `_response` generator was dropped unfinished and marked the
  connection broken; a bad header line went through `_data_errors`, which also marked it broken.
  ARTICLE with a bad header line did the same. So a broken or hostile server forced a reconnect (no
  misread data); the PR keeps the connection usable instead.
- head() at head: `list(self._info(...))` reads to the terminator first; a loss of connection
  inside raises from `_readline`, `_response`'s finally marks it broken (tested). Afterwards
  `_reading` is False, so `_data_errors` does not mark it broken for a parse error. Lines after a
  blank line are dropped, as the new docstring says.
- article() at head: on `ValueError` from `parse_headers` the rest of `lines` is drained, then
  `NNTPDataError` is raised. `parse_headers` is the one raising, so the `_decode` genexp and the
  underlying generator are still suspended and draining continues from the bad line. A
  `UnicodeDecodeError` cannot occur (errors="surrogateescape"), but would be drained the same way. A
  connection loss during the drain marks the connection broken through `_response`'s finally
  (tested). `NNTPDataError` from the gzip path is not a ValueError, so it is not caught here and
  the connection stays marked broken as before.
- Tests: blank line inside HEAD, bad line in HEAD and ARTICLE (each followed by `date()` to prove
  sync), cut-off HEAD and cut-off ARTICLE after a bad line (each followed by NNTPSyncError).

## Notes (not findings)

- `list()` keeps the lines after a blank line in memory until the end of the response. A hostile
  server could make that large, but the same server can already do so with valid header lines (the
  `hdrs` list) or with ARTICLE/BODY, which are joined in memory; not new harm. Parsing from the
  iterator and then draining (as article() now does) would avoid holding the dropped part, if
  wanted.

## Not checked

- No host run; gzip-compressed HEAD with a bad header (by reading it takes the same path).

Score: 9.5
