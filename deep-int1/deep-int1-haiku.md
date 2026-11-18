# deep-int1 review, hk-deep-haiku (Haiku 5.5 high), head e07f041

(Saved by the lead from the reviewer's final message; the reviewer did not write the file itself.)

## Findings

### F1 (Med): LF-only row merged with the next CRLF row in XZVER/XZHDR (and plain OVER/XOVER/HDR)
- Where: nntp/fifo.py:191 readline() finds only CRLF. nntp/nntp.py:508-515 (_lines), 555-564 (_info_plain), 655-664 (_info_yenczlib). The bare-LF check at nntp.py:661-663 only tests `last`, the unterminated tail after the final CRLF.
- Trigger: a buggy server sends XZVER rows with mixed separators, e.g. decompressed payload `1\thello\tme\n2\t.dot\tyou\r\n3\tx\r\n`. The readline yields `1\thello\tme\n2\t.dot\tyou\r\n` as one line; _xover splits it into article 1 with From="me\n2" and loses article 2. No error.
- Test gap: tests/test_overview.py:161-166 passes only because the LF row is in the tail. The docstring at nntp.py:660 says "Rows separated by a bare LF are not one row: refuse them", which the code does not do.
- New or old: the tail check is new in this integration; the plain-response merge is pre-existing in 3.3.0.
- Confirmed by reading. Harm: silent data corruption and row loss. Who: a buggy server mixing LF and CRLF. Exploit: data integrity, shown by reading. Conditions: default config. Verdict: fix soon.

### F2 (Low): from_url error text can contain the password
- Where: nntp/nntp.py:1018 calls urllib.parse.urlsplit(url) before any check; docstring nntp.py:1015-1016 says the message never includes the URL.
- Trigger: a netloc character that NFKC-normalizes to / ? # @ : (U+2100, U+FF0F, U+FF20). CPython's _checknetloc raises ValueError with the whole netloc incl. user:password; it escapes from from_url.
- Pre-existing. Confirmed by reading the stdlib source. Harm: credential in exception text/logs. Who: the caller's own URL. Verdict (reviewer): fix now; wrap urlsplit, re-raise without chaining.

### F3 (Low): ValueError escapes for numbers over 4300 digits
- Where: nntp/nntp.py:1547 (_select int(parts[0])), nntp/yenc.py:93 (int(expected_size)) via nntp.py:653 and 1623; not inside _data_errors.
- Trigger: hostile/buggy server sends a 4301+ digit number; int() raises ValueError (int_max_str_digits). Raw ValueError instead of NNTPDataError; on article/body the next command raises NNTPSyncError.
- Pre-existing. Confirmed by reading. Harm: wrong exception type. Who: hostile server. Verdict: fix soon.

### F4 (Low): header names beginning with "." are sent without dot-stuffing
- Where: nntp/nntp.py:2135 writes the header block raw; utils.py:30 _HEADER_NAME_RE allows a leading ".".
- Trigger: post(headers={".X": "v"}); the server strips the dot, header arrives as "X: v". Pre-existing. Caller mistake, rare. Verdict: issue list or a one-line check.

## Notes (not findings)
N1 XZVER data after the first =yend ignored; no unused_data check after the zlib stream end (by design/docs). N2 XZVER and gzip rows yielded before size/CRC check (streaming). N3 XZVER reply with no yEnc block = empty result. N4 post() return value now first token or "Article received" only (intentional; "240 Article posted <id>" returns True). N5 int() leniency for "+5", "1_000" in XOVER/LISTGROUP numbers. N6 head() buffers whole response; per-operation timeouts let a slow-drip server hold a call. N7 _decode_yenc drops text outside blocks (by design). N8 info()/list() keep CRLF, capabilities()/newnews() strip. N9 each body item without LF ends a line (documented). N10 CI: pull_request, no secrets, read token; faults.yml pins nntp-testkit by tag.

## Not checked
Tests in depth (only spots), no runs, Python 3.14/3.15 specifics, free-threaded builds.

## Score: 7/10
deep-int1: 7, 4 findings (0/1/3): bare-LF rows merged in XZ and plain overviews, from_url error text leaks password for NFKC netlocs, ValueError escapes for >4300-digit numbers, header names starting with "." not dot-stuffed
