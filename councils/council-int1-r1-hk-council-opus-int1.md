# Council int-1, round 1: hk-council-opus-int1 (Claude Opus 5.5)

Head e650e29 (integration-1), base 2bfca17 (3.3.0). Scope: only what the 19
nntp/ PRs do together. Rules files /etc/agents verified (sha512sum -c HASH.md OK);
G1 respected: nothing ran on this machine, apart from reading and git.

## What I did

- Read the whole combined nntp/ diff (int1-nntp.patch) and, at the head, the
  full read/sync path in nntp/nntp.py: `_connect`, `reconnect`, `close`,
  `_sync`, `_recv`/`_decompress`/`_readline`/`_lines`, `status`, `_info_plain`,
  `_info_gzip`, `_inflated_lines`, `_info_yenczlib`, `_info`, `_response`,
  `_data_errors`, `command`/`_unexpected`/`_check_nothing_unread`/`_command`,
  `login`, `NNTPClient._connect`/`__exit__`/`compress`/`quit`, `group`,
  `listgroup`, `_select`, `_read_body`, `_decode_yenc`, `article`, `head`,
  `_hdr`/`_number_values`, `_overview_fields`/`_xover`, `xpat`, `post`, `ihave`,
  `_transfer`, `_prepare_article`; utils.py (`unparse_range`,
  `unparse_msgid_range`, `parse_overview_fmt`, `parse_number_value`,
  `parse_headers`); yenc.py `_KEYWORD_RE`; headerdict.py.
- Checked the merges with git: every line each PR adds in nntp/
  (upstream/main...upstream-pr/N) is present at the head, except the two
  docstrings merged by hand (#170/#171 `_info_yenczlib`; the merged text covers
  both) and #174, whose head on integration-1 carries follow-up e339eda
  (keyword-only `allow_msgid`) that the fetched ref upstream-pr/174 (9004229)
  does not have (see notes). Every PR head except #174 is an ancestor of
  integration-1. Every `test_*` function each PR adds exists at the head.
- Ran one probe on a test host (job 514 on 10.10.11.105, via vm-run.sh): a
  pytest file of 11 cross-PR scenarios x 3 recv chunk sizes in a scratch copy
  (/home/fed/.claude/jobs/b746665a/tmp/int1-hk/tests/test_int1_interactions.py).
  Result: 32 passed, 1 failed; the failure is the expected #187 limit (note 3),
  not an interaction. Scenarios:
  1. #174 row rejected via `_data_errors` (marks broken), then reconnect(), a
     new listing half-read on the new connection, then the old iterator freed
     and gc'd: the new listing finishes and DATE works (#168 identity check
     protects the new connection).
  2. #180 failed reconnect (ConnectionRefused) with a half-read iterator: old
     iterator raises NNTPSyncError (#168), commands raise NNTPSyncError, a later
     reconnect() works, and freeing the old iterator changes nothing.
  3. ARTICLE with a bad header line (#185 drains the body), then DATE: #187
     finds nothing unread, DATE works.
  4. HEAD with a bad continuation line under COMPRESS DEFLATE (#185 + #187's
     `_inflate_more` path), then DATE: works.
  5. GROUP with a malformed number (#173): NNTPDataError, still in sync, DATE
     works.
  6. XZHDR with a second =ybegin after the trailer (#170) and an unterminated
     last row (#171): first row yielded, then NNTPDataError; the last row is
     never yielded; the connection is marked broken; reconnect works.
  7. XZHDR range request whose unterminated last row is a message-id (#171 +
     #174): NNTPDataError "numeric request", broken.
  8. XZHDR by message-id with an unterminated message-id row: (0, value), in
     sync.
  9. POST under COMPRESS with body items `[b"a\n.b\n", b"", b"c"]` and INN's
     "240 Article received <n@x>": items split and dot-stuffed (#182), id
     returned (#169), DATE works after (#187).
  10. POST where 340 and a fake 240 arrive in one packet (#187 in `_transfer`):
      NNTPProtocolError before the body is sent, then NNTPSyncError. Passes
      with chunk 7 and 4096, fails with chunk 1 (note 3).
  11. `xover((True, 2))`, `xover("")`, `xover("  ")`, `article(False)`:
      ValueError and nothing sent, so #176/#179 run before #175's LIST
      OVERVIEW.FMT.

## Interactions checked by reading (no defect found)

| Shared path | PRs | Result |
|---|---|---|
| close()/reconnect() state | #168, #180, #187 | close() sets `_broken`, clears `_reading`, replaces `_buffer`; `_connect` replaces `_buffer` again before `create_connection` and clears `_broken` only after the socket is open; every later failure goes through `close()`. An iterator from before the call always sees a different buffer, both after a failed and a good reconnect; its `finally` never touches the new connection. `_data_errors`' early `_reading=False, _broken=True` and the later GC of the old iterator are both harmless after reconnect (probe 1). |
| Parser errors mid-response vs sync state | #170, #171, #173, #174, #175, #178, #185, #187 | Every parser error inside a response goes through `_data_errors` (marks broken while reading) or is raised from inside the response generator (`_response` finally marks broken). #185 makes ARTICLE/HEAD header errors leave the connection in sync (drained/read in full, `_reading` already False so `_data_errors` does not mark it). #173 is a single-line reply: in sync. Nothing leaves unread data while claiming sync, so #187's new check never fires on a library-made state, only on extra server data. |
| #187 check vs other buffered data | #187 with gzip, COMPRESS, STARTTLS, 480 retry, `_unexpected` | `_info_gzip` only puts back bytes after the response terminator (server excess). `compress()` decompresses pending bytes; `_check_nothing_unread` flushes `_inflate_more` output first, so a 64 KiB-exact last read or a sync flush does not trip it. STARTTLS keeps its own post-382 check (no command follows before TLS): not a duplicate. The 480 path reaches `login()` -> `_command` -> check: fine. `_unexpected` reads the block without the check: right. |
| post()/ihave() | #169, #182, #187 | Body is fully prepared (#182 split, dot-stuffing, CR/NUL check) before POST/IHAVE is sent; `_check_nothing_unread` after the ready reply inside its own `_sync`; #169 parses only the final message. Both #169 and `_select`/`ihave` use the one `_MESSAGE_ID_RE` now in utils.py (moved by #174): no duplicate regex. |
| yEnc readers | #170, #171, #178, #181, #183 | `_info_yenczlib`: trailer, mismatch, second =ybegin, inflate eof checked before #171 yields the unterminated last row, so a bad stream never yields it (probe 6). `_decode_yenc`: #178's open-block =ybegin error and #170's `dropped` flag are independent (dropped only changes outside a block and is reset at every =yend). #183's lookbehind changes no match (a failed `\w+=` at a word start fails at every later start in the same word), only the run time; used by both readers via `parse_keywords`/`check_trailer`. #181 keeps `data` and `__dict__`. |
| Argument validation before sending | #176, #179, #186 | `_xover` now computes args before `overview_fmt`; `_hdr`, `xpat`, `listgroup`, `article/head/body/stat` validate before `command()`. Bare bool range was already rejected in 3.3.0; #176 adds tuples, #179 blank strings and bool msgid/article. Same exception type (ValueError) everywhere. #186 validates before any socket work. |
| #172/#184/HeaderDict | #172, #184, #185 | parse_headers' list-of-pieces form works with both the lazy ARTICLE path and HEAD's list; `copy()` works for `_from_fields` instances (state is the `__dict__`). |

## Findings

None. Nothing found that passes the Findings test for the combination.

## Notes (not findings)

1. **upstream-pr/174 vs integration-1.** The fetched ref upstream-pr/174
   (9004229) still has positional `allow_msgid`; integration-1 merges follow-up
   e339eda (keyword-only), which is on origin/fix/158-number-value. Before
   merging upstream, check that PR #174's head on GitHub is e339eda (or later),
   or the tested combination is not what lands. Either definition works with
   the integration call site; the PR alone is self-consistent either way.
2. **Brief vs code.** The brief says #178 also covers XZVER's yEnc reader; it
   does not: #178 touches only `_decode_yenc`, and the "second =ybegin after the
   trailer" check in `_info_yenczlib` comes from #170. A =ybegin before the
   first =yend in the XZ reader is still decoded as data (pre-existing in 3.3.0;
   normally caught by the CRC check).
3. **#187 sees only data already received** (probe 10 fails with recv chunk
   1: the fake 240 still in the socket is taken as the article's reply). Design
   limit of a buffer check; with real TCP and 4096-byte recvs a reply sent in
   one segment is caught. Hostile server only: Low, and #187's own scope.
4. **Errors raised after the terminator mark the connection broken** although
   it is in sync: XZ reader trailer/CRC mismatch (3.3.0), #170 second =ybegin,
   #171 bare LF. Conservative and consistent across the PRs; costs a
   reconnect, no desync.
5. **#168 per-line cost.** `_response` replaced `yield from` with a Python loop
   (identity check plus try/except per line). Not measured; likely small next
   to decoding.
6. `group()` still catches `IndexError`, unreachable after #173's length check
   (style).
7. `hdr()`/`xpat()` with a range passed as a str ("1-5") get `allow_msgid=True`
   (#174 alone; only a weaker check, no harm).
8. My probe file is test-only and has ruff errors (imports inside a function,
   long lines); it is not meant to be merged.

## Not checked

- tests/ and CI changes (#145 fault tests, #153 CI, #167 integration tests,
  #177 ruff config) beyond the presence of every PR's test functions and the
  e650e29 marker commit message; the full unit, fault and INN suites were not
  rerun by me (lead's facts).
- TLS (implicit/STARTTLS) and `from_url` beyond reading the #186 lines;
  XFEATURE COMPRESS GZIP beyond reading; behaviour on Python other than the
  test host's; performance.
- Each PR's own logic in isolation (out of scope by the brief).

## Score

9.6. The 19 PRs merge together safely as they are: the shared sync paths agree
(every error leaves the connection either in sync with nothing buffered or
marked broken), no check was dropped or duplicated by the merges, and
validation runs before anything is sent. Not 10 because of note 1 (the PR #174
ref must match what was tested) and the untested gzip/TLS corners.

int-1: 9.6, 0 findings (0/0/0): -
