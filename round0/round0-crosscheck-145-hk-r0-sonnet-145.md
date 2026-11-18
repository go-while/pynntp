# Round-0 cross-check of #145 (hk-r0-sonnet-145), head 9b0db18, by reading

Lead's fact: host 116, 220 passed, 8 xfailed. That matches my count of the markers (3 leftover + session + xzver x2 + yenc + group = 8), so none XPASSes today.

## H1 (Haiku, Med) positive controls accept errors: confirmed in part, I rate it Low

- compress/stream-finished-exactly (scenarios.py:1417-1424) is Clean(pred == PROBE_TUPLE), probe=None. judge_error returns "" for any NNTPError/OSError, so a regression that rejects a finished stream passes. True. Today nntp.py:403-407 returns the data (no unused_data), so Ok(PROBE_TUPLE) would pass now. But the project does not say a finished stream must be accepted (RFC 8054: the stream lasts as long as the connection), so Clean is a deliberate "either, but clean" pin. Tightening is a choice of the author, not a wrong verdict. Triggers only on a change of this exact behaviour. Low.
- xzver/data-after-deflate-end (:1616): the comment says "accepted (observed)"; Clean(pred=over_check) lets a later rejection pass too. Same reasoning, Low.
- post/early-441-then-close (:1805): refuted as a defect. The server sends 340+441 then closes while the client uploads 4 MB, so the client sees the 441, EPIPE or a reset depending on timing. Err(NNTPTemporaryError, match="441") would be flaky; Err(*CLEAN_ERRORS) is the right choice here.
- Score effect: none (Low, can be fixed by Ok(...) for the first two if the lead wants a stricter control).

## H2 (Haiku, Low) Clean-with-value skips the state check: confirmed, by design

judge_value (2439-2442) returns "" for Clean before the state test, so leftover/crlf-after-terminator (:923) passes if the next command raises any clean error and the connection is "late-broken". This is what Clean's docstring says ("in sync or marked broken"; desync is rejected earlier at run_client). The comment at :925 says the connection "ends up marked broken", which the verdict does not pin. Documentation/precision issue only. Low, no score effect.

## H3 = S1: same as my finding 1 (1619, 1620, 1730). Unchanged.

## H4 (Haiku, Low) server mismatches are not failures unless opted in: confirmed, mitigated

run() never looks at summary["mismatches"]; only 8 definitions use no_mismatch (lines 838, 850, 1169, 1776, 1784, 1824, 2060 and article_is). v0.13.0 answers a non-matching line with "500 unexpected" (read in main.go), so the client sees an error. That fails every Ok scenario. It is masked only in Clean and Err(state="any") scenarios and in Err scenarios whose type a 500 happens to satisfy (NNTPPermanentError is an NNTPReplyError). Trigger: a client regression that sends a wrong or extra command in one of those scenarios. Low; a generic "no mismatches unless the scenario says otherwise" rule in run() would close it, but then scenarios that intentionally provoke 500 need an opt-out. No score effect.

## Score

None of H1, H2, H4 changes my view: all Low, no wrong verdict that hides a bug found today, and the host run is clean. My score stays 9; what keeps it from 9.5 is S1 plus the Low precision points above (H1 first two cases, H4).

#145: 9, 1 findings (0H/0M/1L) after cross-check: known_why of 3 markers too broad; H1 (Low, not Med), H2 and H4 (Low) confirmed as notes
