# Round-0 cross-check #173-#176, hk-r0-sonnet-b (read-only; no runs, git and gh reads only)

## 1. #174: message-id row still gets number 0 in range answers (confirmed, pre-existing, half of #158 open)
- utils.py parse_number_value() at cfac120: `_MESSAGE_ID_RE.fullmatch(first)` -> number 0 whatever the query was; the parser does not know it. Same as my note.
- Trigger: only a broken or hostile server (a numeric or current-article query answered with `<id> value` rows). Callers get (0, value) instead of an error; wrong article number, silent. Low, pre-existing, not new in the PR.
- Should the PR cover it? The PR body states it and says why not ("would mean tracking which request a row answers"). That reasoning is weak: the request is known at the call sites. `_hdr()` (nntp.py ~1561) and `xpat()` have `msgid_range`; a flag `allow_msgid = isinstance(msgid_range, str)` passed through `_number_values()` to `parse_number_value()` is a handful of lines. Recommendation: either add it (preferred, the issue asks for it, and it keeps the legacy XHDR-by-message-id echo working), or change "Fixes #158" to "Refs #158"/"Part of #158" so the issue stays open. As written, "Fixes #158" auto-closes an issue that is half done. Score 9 -> 8 for that, not for a bug in the code.

## 2. #174: a malformed "<" token now breaks the connection (acceptable, partly refuted)
- The break is not a new policy of this PR: `_data_errors()` (nntp.py:596-607) marks the connection broken for every row parse error in a multi-line reply, because the rest of the reply is unread; the PR body says so. Base "stayed in sync" only because it accepted the garbage (number 0), i.e. returned a wrong number silently.
- A server sending `<broken value` rows is broken or hostile; loud failure plus reconnect() is the right trade, and equal to what NEWGROUPS, LISTGROUP and OVER rows already do. Optional improvement (not needed here, module-wide): drain the rest of the reply before raising so the session survives. No score change.

## 3. #175: one odd OVERVIEW.FMT name makes every OVER/XOVER fail (confirmed behaviour, fallback not right)
- Confirmed: utils.py:156-157 raises; list_overview_fmt() (nntp.py:1236) turns it into NNTPDataError and breaks the connection; `_overview_fields` (cached_property) caches nothing on error, so each over() re-sends LIST OVERVIEW.FMT and fails again; reconnect gets the same list. Trigger: a broken server (real ones send "Name:", "Name:full", ":bytes"). Low. New in the PR, by intent of #164.
- Fallback judgement: for a client library, raising is right. OVER rows are positional, keyed by this list. Skipping a line shifts every later column, and using the RFC default format when the server's real format differs mislabels values, so both turn a loud failure into silently wrong data (subject under the wrong key), which is worse than the current "base gave silently wrong keys" case. The existing fallback is only for a 5xx reply (no list at all), where the default is the documented guess; a bad line is not that case. Two cheap things that would help without guessing: drain the rest of the list before raising (keeps the session usable for other commands, e.g. hdr()), and the error text names the line. Not required for merge. No score change.

## 4. #173 and #145: the strict xfail must go with #173 (confirmed)
- Checked refs/pull/145/head (133c09b): tests/faults/scenarios.py:2071-2078 `malformed/group-negative-numbers`: script GROUP g -> `211 -5 -3 -9 g`, expects Err(NNTPDataError, state="sync"), `known="group() accepts negative numbers in the 211 reply"`, `known_why="expected NNTPDataError, got result"`. test_faults.py:29-30 uses strict xfail (`strict=sc.known_strict`, default True).
- With #173 the call raises NNTPDataError. group() raises after the single status line, outside `_data_errors`, so the state stays "sync". The scenario then passes, XPASS under strict xfail fails the run. The README of #145 (tests/faults/README.md:83, table row `malformed/group-negative-numbers` ... #157) says the same: "remove known= and known_why in the same change".
- So whichever of #145/#173 merges second must remove `known=`/`known_why=` of that scenario and the README row (and the scenario's #157 mention). Same check for my other three PRs: #145 has no known-marker for #158, #164 or #165 (the only known rows are #161, #162, #154, #160, #159, #157), so nothing else to remove. The OVERFMT scenarios at scenarios.py:498, 1594, 2089, 2099 use valid formats; unaffected by #175.
- Order/merge note: #145 and #173 touch different files, so no textual conflict; only the strict-xfail interaction.

## Updated scores
#173: 9, 0 findings (H/M/L): - (note: #145 xfail marker must be removed by whichever lands second)
#174: 8, 0 findings (H/M/L): - (note: half of #158 still open, change "Fixes" to "Refs" or add the allow_msgid flag)
#175: 9, 0 findings (H/M/L): -
#176: 9, 0 findings (H/M/L): -
