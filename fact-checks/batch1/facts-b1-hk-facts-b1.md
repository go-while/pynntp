# Fact check, batch 1 (#182, #183, #185, #186, #171): hk-facts-b1 (Claude Opus 5.5)

Base: upstream/main 2bfca17 (3.3.0). Heads: upstream-pr/182 2ddb15b, 183 54751e2, 185 edbe199, 186 9a3379d, 171 8ac5794. Every PR's merge base is 2bfca17. The live PR bodies (fetched with `gh pr view <n> -R greenbender/pynntp --json body`) are byte-identical to pr-texts.md, and the live head SHAs match.
Method: I read the code with git (base and head). There was one optional test-host timing run for #183 (jobs 992 and 993, see #183 C3). Nothing ran on this machine. My two temporary worktrees were removed afterwards.

## Findings

| # | PR / claim | Sev | What is wrong | Corrected wording |
|---|---|---|---|---|
| F1 | #183 C3 | Low | "took about 45 s of CPU" is presented as a measurement, but nobody measured it at 64 KB or through body()/article(). The figure is an extrapolation: an internal review note S1 timed a copy of the regex at 4k, 8k and 16k (0.17, 0.69 and 2.78 s), and 2.78 x 16 is about 44.5 s. The commit message says "tens of seconds". My test-host run on base 2bfca17 (job 992, host .114) measured 65,000 bytes of "a": parse_keywords() took 63.47 s of CPU, and body() on an article with that =ybegin line took 65.93 s. At the head (job 993, .105) the same calls took 0.01 s. So 45 s is the right order of magnitude but not a measured value. | "A poster's article with a `=ybegin ` line followed by about 64 KB of `a` took about a minute of CPU in `body()` or `article()` (65 s measured on a test host, through `_decode_yenc` and `parse_keywords`; the time depends on the machine)." Or keep the commit's "tens of seconds". |
| F2 | #186 C4 | Low | The text says the from_url() docstring states that `ssl_mode` and `ssl_context` only take effect with use_ssl=True and that an invalid ssl_mode raises ValueError. The from_url() docstring at the head (nntp/nntp.py:870-871) only says "An ssl_context only takes effect with an nntps://, snews:// or nntp+starttls:// URL". It mentions neither ssl_mode (from_url() takes no ssl_mode; FromURLOptions, nntp.py:80-87) nor ValueError. The README sentence (README.md:49-52) names only `nntps://` and `nntp+starttls://`, not `snews://`. The constructor docstrings (nntp.py:288-300 and :829-840) do say all of it. | "The constructor docstrings and the README say that `ssl_mode` and `ssl_context` only take effect with `use_ssl=True` (which an `nntps://`, `snews://` or `nntp+starttls://` URL sets), and that an invalid `ssl_mode` raises `ValueError`; the `from_url()` docstring says an `ssl_context` only takes effect with such a URL." |

No High or Med findings.

## Claims

### #182 (head 2ddb15b)
| Claim | Verdict | Evidence |
|---|---|---|
| C1 base: each body-iterable item was treated as one line; only CR and NUL were refused | shown | base nntp.py:1892-1906. `for line in body` runs on the items, strips only a trailing LF/CRLF and checks only `\0` and `\r`. |
| C2 base: `[b"x\n.\nQUIT\n"]` was sent as "x\n.\nQUIT\r\n" | shown (by reading) | Same loop: the item has no leading ".", its trailing LF is stripped, and CRLF is appended. Both round-0 reports agree. |
| C3 a bare-LF server sees the lone "." as the end; the rest is read as commands | shown (reasoning, consistent with the code) | The bytes on the wire are "x\n.\nQUIT\r\n" followed by ".\r\n" (C2). |
| C4 head: items are split at LF by `_item_lines()`; the example is sent as `x\r\n..\r\nQUIT\r\n` | shown | head nntp.py:171-180 and :1914-1915. Test test_post_body_item_lines_are_split, case 1, checks the exact bytes. |
| C5 an item without LF still ends a line; an empty item is an empty line; str/bytes bodies are unchanged | shown | `_item_lines` yields b"" for an empty item, and BytesIO yields a last chunk that has no LF. The str/bytes path is still `io.BytesIO(body)`. Test cases 4 and 5. |
| C6 the CR/NUL check runs on the split lines; CRLF is fine; any other CR or a NUL raises NNTPDataError before anything is sent | shown | The loop at :1917-1926 runs on the split lines. `_transfer` (:1879-1890) prepares the article before `command()`. test_post_iterable_illegal_chars_sends_nothing asserts `sock.sent == b""`. |
| C7 the post() and _prepare_article() docstrings say this | shown | head :1805-1808 and :1903-1905. |
| C8 test coverage list | shown | test_post_body_item_lines_are_split (5 cases), test_ihave_body_item_lines_are_split, test_post_iterable_illegal_chars_sends_nothing (4 cases). |
| C9 "council r1: opus 9.6, sol 10 (round 0: haiku 9, sonnet 9)" | shown | council-fix-post-body-item-lines-r2b-hk-council-opus-d.md 9.6; ...-r2b-pynntp-sol-low.md 10; round0-...-hk-r0-haiku.md 9; round0-...-hk-r0-sonnet.md 9. The files are named "r2b" after the batch round (tasks/council-r2b.md). For this PR it was its first council round, so "r1" is consistent. |
| extra: "It happens when an item holds several complete lines" | shown | Follows from C1 and C2. |

### #183 (head 54751e2)
| Claim | Verdict | Evidence |
|---|---|---|
| C1 base `_KEYWORD_RE` was `(\w+)=(\S*)` | shown | base nntp/yenc.py:27 |
| C2 findall retried `\w+` from every start; the cost grew with the square of the line length | shown | By reasoning: each start inside a word run scans to the end of the run and backtracks. My host timings are 16k 3.57 s, 32k 15.68 s and 65k 63.47 s, about 4x per doubling (job 992). |
| C3 about 45 s of CPU in body()/article() for about 64 KB | not shown as stated (F1) | See F1. A direct measurement gives about 65 s. |
| C4 the =yend line goes through check_trailer the same way | shown | base nntp.py:1459 `check_trailer` -> yenc.py `parse_keywords`. =ybegin is at :1457. |
| C5 head pattern `(?<!\w)(\w+)=(\S*)`, linear | shown | head yenc.py:29. Host: 65k in 0.01 s (job 993). |
| C6 results are the same as before for every line | shown (reasoning) | From any start inside one word run, `\w+` can only reach the "=" at the end of that run, so all starts in a run succeed or fail together and the leftmost one wins. `\S*` ends at whitespace, so the next search never starts mid-word. The table test pins the cases. Both r2b reviewers reach the same conclusion. |
| C7 test coverage list | shown | test_parse_keywords_table (a-b=c, x=1x=2, ==4 a==5, 9z=2, full =yend), test_parse_keywords_long_word_run_is_linear (2 x 65536, < 1.0 s), test_body_yenc_long_word_run_keeps_sync (60000 on =ybegin and =yend). |
| C8 "council r2: opus 9.6, sol 10" | shown | council-fix-yenc-keyword-regex-r2b-hk-council-opus-e.md 9.6; ...-r2b-pynntp-sol-low.md 10. This is the second round after r1 (opus-a 9, sol 10). |

### #185 (head edbe199)
| Claim | Verdict | Evidence |
|---|---|---|
| C1 parse_headers() stops at the first blank line or a non-header line | shown | base utils.py:198-215. It breaks on a blank line. On a non-header line it stops by raising ValueError, which the text then describes. |
| C2 base: a blank line inside HEAD left the rest unread; the dropped iterator marked the connection broken; the next command raised NNTPSyncError | shown (by reading) | base head() :1534-1536 returns before the iterator is exhausted. `_response` finally (:584-595) sets `_broken`, and `_command` (:680-686) raises NNTPSyncError. The new test test_head_blank_line_inside_headers fails on the base, per the tracker ("head-read:12"). |
| C3 base: a header line without a colon raised NNTPDataError with the rest unread; _data_errors() marked the connection broken | shown | base `_data_errors` :599-611 sets `_broken` while `_reading`. head() and article() both use it. |
| C4 head: head() reads everything, then parses; lines after a blank line are read and ignored; a bad line raises "Invalid article headers: ..." with the connection in sync | shown | head :1547-1549: `list(self._info(...))`, then `_data_errors("article headers")`, where `_reading` is already False. Tests test_head_blank_line_inside_headers and test_head_bad_header_line_keeps_connection. |
| C5 article() reads the rest before raising NNTPDataError | shown | head :1506-1513 |
| C6 both docstrings say this | shown | head :1493-1495 (article) and :1535-1541 (head) |
| C7 a connection lost while reading the rest raises the usual error and marks the connection broken | shown | `_response` finally. Tests test_head_connection_lost_breaks_connection and test_article_bad_header_then_connection_lost_breaks_connection. |
| C8 test coverage list | shown | The 5 new tests in tests/test_articles.py. |
| C9 "council r2: opus 9.5, sol 10" | shown | council-fix-head-read-all-r2b-hk-council-opus-e.md 9.5; ...-r2b-pynntp-sol-low.md 10. This is the second round after r1 (opus-a 9, sol 10). |
| extra: Behaviour change paragraph | shown | Same evidence as C4 and C5. |

### #186 (head 9a3379d)
| Claim | Verdict | Evidence |
|---|---|---|
| C1 base compared ssl_mode only with the two members; "STARTTLS"/"tls" took neither branch even with use_ssl=True | shown | base nntp.py:301, :321 and :328 use `==`. SSLMode is a StrEnum (types.py:23), so only "implicit" and "starttls" compare equal. |
| C2 the example connected in plain text on port 119 and sent the login/password in clear on a 480 | shown (by reading) | The port is 119 because the mode is not IMPLICIT (:301). On a 480, command() and NNTPClient._connect log in (docstring :648-650). |
| C3 head: SSLMode(ssl_mode) runs first with use_ssl=True; members and their values work; anything else raises ValueError before a socket is opened; with use_ssl=False there is no check | shown | head :302-304 runs before `_connect`. test_invalid_ssl_mode monkeypatches create_connection to fail, and test_ssl_mode_ignored_without_use_ssl covers use_ssl=False. |
| C4 docs (constructors, from_url, README) | partly wrong (F2) | Constructors: shown. from_url(): only the ssl_context sentence. README: no snews. |
| C5 ssl_context with use_ssl=False or nntp:// is still accepted and ignored | shown (by reading) | No check in the head. `_enable_tls` only runs under `_use_ssl`. from_url passes `ssl_context` through `settings` (:895-906). |
| C6 test coverage list | shown | test_invalid_ssl_mode (tls, STARTTLS, "", None, 1), test_ssl_mode_ignored_without_use_ssl, test_default_port with "starttls"/"implicit", test_tls_url_uses_ssl_context (nntps, snews, nntp+starttls). |
| C7 "council r2: opus 9.5, terra 9.5" | shown | council-fix-ssl-context-plaintext-r2b-hk-council-opus-e.md 9.5; ...-r2b-pynntp-terra-high.md 9.5. See note N1 on the round number. |
| extra: "Valid values, including the lower-case strings, behave as before" | shown | StrEnum equality on the base. The head converts to the member, so the branches are the same. |

### #171 (head 8ac5794)
| Claim | Verdict | Evidence |
|---|---|---|
| C1 base dropped a last row without CRLF silently, although the stream was complete and size/CRC were correct | shown | In base nntp.py:543-566, `buf` is never read after the checks. BytesFifo.readline only returns CRLF-terminated lines (fifo.py:113-134). |
| C2 after the trailer and eof checks pass, the remaining row is returned without an added CRLF; the parsers don't need one | shown | head :567-572. `_xover` uses `line.rstrip("\r\n")` (:1671), and `parse_number_value` rstrips (utils.py:177). |
| C3 remaining data with a bare LF raises NNTPDataError | shown | head :569-570. Tests test_xzver_lf_only_rows and test_xzhdr_lf_only_rows. The wording "remaining data" is accurate: only the data after the last CRLF is checked. |
| C4 the line-length, CRC/size and truncation checks are unchanged; on failure the partial row isn't returned | shown | The yield comes after all checks. `_lines` already raises if `len(buf) >= max_line_length`. Test test_xzver_unterminated_row_bad_trailer. |
| C5 #145's known-failure marker for xzver/last-row-without-crlf goes when this merges | shown | At #145's live head f789662 (= origin/port/fault-tests), tests/faults/scenarios.py:1589-1595 sets `known`, :1642-1645 sets known_why, and README.md:92 maps it to #160. test_faults.py:29-30 uses strict xfail, so an XPASS fails the run and the marker has to go. Note: the local ref upstream-pr/145 (ae27409) is stale; the marker is the same there. |
| C6 test coverage list | shown | test_xzver_last_row and test_xzhdr_last_row (rows 1/2 x terminated), test_xzver_empty_compressed_stream, test_xzver_unterminated_row_bad_trailer. |
| C7 "Fixes #160": #160 exists and describes this bug | shown | `gh api repos/greenbender/pynntp/issues/160`: open, "XZVER/XZHDR drop a last row without CRLF silently". |
| C8 "council r1: opus 9.5, sol 9.5" | shown | council-pr171-r1-hk-council-opus-f.md and council-pr171-r1-sol-oneshot.md. The tracker line 56 has #171 at 9.5 for both. |

## Notes (not findings)
- N1: #186's "r2" scores come from the r2b files. That PR also had an earlier r2 (opus-c 9, sonnet 9, on d0a1e04/9a3379d). The r2b brief calls itself "round 2 for the batch", so "r2" is defensible. Strictly, it was the third review set for #186. #182 calls the same r2b batch "r1". Both labels are consistent per PR.
- N2: GitHub REST shows #182, #183, #185 and #186 still as **draft=true** (updated 16:09Z). Only #171 is ready (draft=false). The brief and the tracker say all five were marked ready for review. The lead should check ready-batch-1b.sh.
- N3: #185 "HEAD responses are small" is a reason, not a fact the code enforces. head() now buffers the whole response; each line is still capped by max_line_length.
- N4: #171 CI at 8ac5794: all check-runs succeeded (3.11-3.15t, test-inn2, label).

## Not checked
- The other PRs' tests were not run (only the #183 timing). Exact wire bytes elsewhere are shown by reading the tests and code, not by a run.
- Whether the #145 scenario actually passes with #171 merged (not shown by reading; the tracker says the integration-1 fault suite ran).

facts-b1: 46 claims checked, 2 findings (H/M/L 0/0/2): #183 "about 45 s" is an extrapolation (65 s measured on a host); #186 from_url docstring/README do not say all that is attributed to them
