I’ll check behaviour against the base and supplied diffs, then verify the measurements, scores, and cross-PR references separately. I won’t run tests or timing probes on this workstation.
The core fixes are supported by the code and tests. I’ve found documentation/provenance issues, including #185’s title: ARTICLE still parses headers while reading and drains the remainder only after a parse error.

Live GitHub metadata also differs from the task setup: #182, #183, #185, and #186 are still drafts; #171 is ready. I’ll keep that separate from findings about the PR texts.
## Outcome

**49 claims checked; 9 findings: 0 High, 1 Med, 8 Low.** The core behavioural fixes are supported. Findings concern wording, documentation references, review-round labels, and attribution provenance.

Counting: the 41 supplied claim IDs, three additional substantive claims, and five “Generated with Claude Code” attributions. Repeated statements are counted once.

### Evidence notation

- **B**: files in the supplied base checkout.
- **H182**, etc.: the corresponding head section of the attached `b1.patch`.
- Report filenames below are under `upstream-gap/`.
- **Shown** means supported by source, reasoning, tests inspected, or an explicitly identified report—not that I independently ran tests.

## Claim ledger

### #182 — head `2ddb15b`

| Claim | Verdict | Evidence |
|---|---|---|
| C1: iterable items were treated as individual lines; CR/NUL refused | **Shown** | B `nntp/nntp.py:1892–1906`: only whole `str`/`bytes` bodies become `BytesIO`; other iterables are processed item-by-item. |
| C2: example emitted `x\n.\nQUIT\r\n` | **Shown** | B `nntp/nntp.py:1899–1906`: only the item’s final LF is removed; the interior dot is untouched. |
| C3: an LF-tolerant server can terminate the article early and read the remainder as commands | **Shown** | The emitted interior `\n.\n` supplies precisely that delimiter to such a server. Also explained in `council-fix-post-body-item-lines-r2b-hk-council-opus-d.md:7`. Conditional on the stated server behaviour. |
| C4: LF splitting and corrected example bytes | **Shown** | H182 `nntp/nntp.py:171–180,1912–1926`; exact-wire assertions in `test_post_body_item_lines_are_split` and `test_ihave_body_item_lines_are_split`. |
| C5: unterminated/empty-item semantics retained; `str`/`bytes` unchanged | **Shown** | H182 `_item_lines()` and `_prepare_article()`; corresponding parametrized cases in `tests/test_posting.py`. |
| C6: per-line CR/NUL validation; CRLF accepted; rejection before sending | **Shown** | H182 preparation loop; B `_transfer()`, `nntp/nntp.py:1871–1876`, prepares before issuing POST/IHAVE. New illegal-character tests assert `sock.sent == b""`. CRLF must remain within an item. |
| C7: both docstrings describe item boundaries and LF splitting | **Shown** | H182 `post()` and `_prepare_article()` docstring hunks. |
| C8: stated test coverage | **Shown** | H182 `tests/test_posting.py`: both exact-wire tests, five body-shape cases, and four iterable illegal-character cases. |
| C9: council/round-zero score line | **Wrong — F2** | Scores exist, but the 9.6/10 reports are labelled **r2b**, not r1. Round-zero Haiku/Sonnet scores of 9 are shown in `round0-post-body-item-lines-hk-r0-{haiku,sonnet}.md`. |
| Additional: text after an interior LF was “neither dot-stuffed nor ended with CRLF” | **Wrong — F1** | The PR’s own example ends `QUIT\r\n`; B `nntp/nntp.py:1902–1906` normalizes the item’s final ending. Interior endings were the problem. |

### #183 — head `54751e2`

| Claim | Verdict | Evidence |
|---|---|---|
| C1: original regex | **Shown** | B `nntp/yenc.py:27`. |
| C2: quadratic retries on word runs without `=` | **Shown** | B `nntp/yenc.py:27,44–47`; successive starting positions retry successively shorter suffixes. `deepfix-review-opus.md:30–44` supplies the same argument. |
| C3: approximately 45 seconds CPU for approximately 64 KB | **Shown, as a reported measurement** | `cross-project-patterns-2026-11-14.md:7` explicitly records this figure and test-host timing. `an internal review note:12` records the figure and smaller-run timings; `deepfix-review-opus.md:20` reports about 90 seconds for the two-run base timing test. Reachability through BODY/ARTICLE: B `nntp/nntp.py:1407–1413,1455–1459,1506,1562`. See measurement limitation below. |
| C4: trailer parsing has the same exposure | **Shown** | B `nntp/nntp.py:1458–1459`; `nntp/yenc.py:73–87` calls the same parser. |
| C5: replacement pattern and linear complexity | **Shown** | H183 `nntp/yenc.py:27–29`. Interior positions fail the fixed-width lookbehind; each word run is scanned from its start rather than every suffix. |
| C6: identical results for every input line | **Shown** | An earlier position in a word run reaches the same `=`; after a match, `\S*` consumes to whitespace/end. Thus a removed interior start could not have supplied an earlier match. Filename exclusion is unchanged. Detailed proof: `deepfix-review-opus.md:38–45`. |
| C7: stated keyword, timing, and BODY tests | **Shown** | H183 `tests/test_yenc.py`: `test_parse_keywords_table`, `test_parse_keywords_long_word_run_is_linear`; `tests/test_articles.py`: `test_body_yenc_long_word_run_keeps_sync`. |
| C8: council score line | **Wrong as an exact round label — F3** | The matching 9.6/10 reports are `council-fix-yenc-keyword-regex-r2b-{hk-council-opus-e,pynntp-sol-low}.md`, not r2-labelled reports. Numeric scores are shown. |

### #185 — head `edbe199`

| Claim | Verdict | Evidence |
|---|---|---|
| C1: header parsing stops at blank/non-header input | **Shown** | B `nntp/utils.py:200–214`: blank line ends parsing; malformed non-continuation line raises `ValueError`. |
| C2: blank HEAD line could return normally but leave a broken connection | **Shown** | B `nntp/nntp.py:1533–1536,585–596,680–686`. Abandoning the unfinished response triggers broken-state handling. |
| C3: malformed HEAD/ARTICLE headers raised with unread remainder and broken state | **Shown** | B `nntp/nntp.py:1503–1505,1535–1536,599–611`; parser error at `nntp/utils.py:211–213`. |
| C4: HEAD fully reads before parsing; trailing lines ignored; parse errors preserve sync | **Shown** | H185 `nntp/nntp.py:1543–1549`; `test_head_blank_line_inside_headers` and `test_head_bad_header_line_keeps_connection`. |
| C5: ARTICLE drains after malformed headers before raising | **Shown** | H185 `article()` try/except and drain loop, approximately `nntp/nntp.py:1503–1514`; corresponding bad-header test checks subsequent DATE. |
| C6: both docstrings describe the respective behaviour | **Shown** | H185 `article()` Raises and `head()` Returns/Raises docstring changes. |
| C7: connection loss propagates the usual error and breaks the connection | **Shown** | B `_recv()` at `nntp/nntp.py:384–386`, `_response()` at `585–596`; H185 HEAD-loss and ARTICLE-drain-loss tests. |
| C8: stated malformed-response/disconnection coverage | **Shown** | All five new tests in H185 `tests/test_articles.py`. |
| C9: council score line | **Wrong as an exact round label — F6** | Matching reports are `council-fix-head-read-all-r2b-{hk-council-opus-e,pynntp-sol-low}.md`: 9.5/10. |
| Additional: title says HEAD **and ARTICLE** read the whole response before parsing headers | **Wrong — F4** | H185 ARTICLE parses the live iterator first and drains only after a parsing failure. This also contradicts the body’s accurate explanation. |
| Additional: “HEAD responses are small” | **Not shown — F5** | B `nntp/nntp.py:416–437` limits individual lines, not aggregate response size. H185 `list(self._info(...))` has no total-size limit. |

### #186 — head `9a3379d`

| Claim | Verdict | Evidence |
|---|---|---|
| C1: invalid nonmatching modes took neither TLS branch | **Shown** | B `nntp/nntp.py:301,321–333`. Lowercase valid strings already compare equal because `SSLMode` is a `StrEnum`: `nntp/types.py:23–31`. |
| C2: example selects plaintext port 119 and can send credentials in clear after 480 | **Shown** | B port/TLS selection above; constructor’s MODE READER authentication path at `nntp/nntp.py:898–907`; login exchange at `755–770`. Password transmission follows the server’s usual 381 password request. |
| C3: conditional enum conversion, accepted values, early rejection, ignored plaintext mode | **Shown** | H186 first addition in `BaseNNTPClient.__init__`; conversion precedes `_connect()`. New invalid-mode and ignored-mode tests cover both conditions. |
| C4: all named documentation locations say the described things | **Wrong — F7** | H186 constructor docstrings and README document the mode/context condition and invalid-mode error. The `from_url()` addition documents only `ssl_context` and TLS URL schemes; it does not document `ssl_mode` validation. Scheme mapping itself is shown at B `nntp/nntp.py:69–73`. |
| C5: plaintext contexts remain accepted and ignored | **Shown** | B/H186 `nntp/nntp.py:304–306,321–333,363–372,889–895`; no plaintext-context rejection is added. |
| C6: stated test coverage | **Shown** | H186 `tests/test_connection.py`: default-port string cases, invalid-mode no-socket guard, ignored modes; `tests/test_from_url.py`: context reaches `wrap_socket` for all three TLS schemes. |
| C7: council score line | **Wrong as an exact round label — F8** | `council-fix-ssl-context-plaintext-r2b-hk-council-opus-e.md:41` and `council-fix-ssl-context-plaintext-r2b-pynntp-terra-high.md:4`: both 9.5, labelled r2b. |

### #171 — head `8ac5794`

| Claim | Verdict | Evidence |
|---|---|---|
| C1: base silently dropped a valid unterminated final row | **Shown** | B `nntp/nntp.py:545–565` yields only complete CRLF rows and never returns the residual buffer. `nntp/fifo.py:24,113–128` searches specifically for CRLF. |
| C2: validated residual row returned unchanged; parsers accept it | **Shown** | H171 `nntp/nntp.py:567–572`; parsers strip optional endings at B `nntp/utils.py:177–179` and `nntp/nntp.py:1663–1666`. |
| C3: bare LF in residual data raises | **Shown** | H171 residual `b"\n"` check and LF-only tests. This is specifically the unterminated tail, not every CRLF-terminated row. |
| C4: existing validation unchanged; failing validation precedes residual-row yield | **Shown** | H171 adds the yield after trailer/size/CRC/EOF checks; existing length checking remains at B `nntp/nntp.py:430–437,553–565`. |
| C5: #145 marker needs to go when the fixes are integrated | **Shown as a merge instruction** | `gh api repos/greenbender/pynntp/pulls/145` identifies the current open go-while PR and its marker/removal policy. `review-pr145-hk-testprs.md:32–43` records strict XPASS with this exact #171 head and says whichever PR lands second must remove the marker. **The supplied #171 diff does not itself remove it.** |
| C6: stated test coverage | **Shown** | H171 `tests/test_overview.py`: both commands × one/two rows × terminated/unterminated, empty compressed stream, bad trailer, plus LF-tail errors. |
| C7: issue #160 exists and describes this bug | **Shown** | `gh api repos/greenbender/pynntp/issues/160`: open issue titled “XZVER/XZHDR drop a last row without CRLF silently”; body describes complete streams losing their last row. |
| C8: council r1, Opus/Sol 9.5 | **Shown** | `council-pr171-r1-hk-council-opus-f.md:1–6`; `council-pr171-r1-sol-oneshot.md:2,11`. |

### Attribution claims omitted from the supplied list

| Claims | Verdict | Evidence |
|---|---|---|
| Each of the five texts was “Generated with Claude Code” — five claims | **Not shown — F9** | The footer asserts provenance, but no generation transcript or tool log was supplied. `deep-fixes-status.md:61` records Sonnet/cc-1 drafting/review, not verification of the specific generating tool. |

## Findings and exact corrections

| ID | Severity | Finding | Exact corrected wording |
|---|---|---|---|
| **F1** | Low | #182 overstates the missing CRLF normalization | “Interior LF-separated lines were not individually dot-stuffed or normalized to CRLF; only the item’s final newline was normalized.” |
| **F2** | Low | #182 wrong council round | `council r2b: opus 9.6, sol 10 (round 0: haiku 9, sonnet 9)` |
| **F3** | Low | #183 imprecise council round label | `council r2b: opus 9.6, sol 10` |
| **F4** | Low | #185 title contradicts ARTICLE’s implementation/body text | “HEAD and ARTICLE: consume the response before reporting malformed headers” |
| **F5** | **Med** | #185 unsupported size assurance could justify buffering on a false premise | “`head()` buffers the whole response before parsing it. Individual lines are length-limited, but the total response size is not.” |
| **F6** | Low | #185 imprecise council round label | `council r2b: opus 9.5, sol 10` |
| **F7** | Low | #186 overstates what `from_url()` documents | “The constructor docstrings and README document that `ssl_mode` and `ssl_context` take effect only with `use_ssl=True`, and that an invalid mode then raises `ValueError`. The `from_url()` docstring documents which URL schemes enable use of `ssl_context`.” |
| **F8** | Low | #186 imprecise council round label | `council r2b: opus 9.5, terra 9.5` |
| **F9** | Low | Unverified generation attribution in all five texts | Delete `🤖 Generated with [Claude Code](https://claude.com/claude-code)` unless its provenance can be established. |

## Notes and limits

- **Live readiness differs from the task setup.** `gh pr view <n> -R greenbender/pynntp --json number,title,headRefOid,isDraft,body` returned `isDraft:true` for #182, #183, #185, and #186; #171 returned `false`. All five head SHAs and bodies matched the supplied material. This is task-context metadata, not a finding inside a PR description.
- The approximately 45-second figure has report support. I did not independently repeat it. The detailed original verification describes regex-copy timings; it is not a raw end-to-end BODY/ARTICLE CPU log.
- #145’s current head is `f789662eba9feba460cfbb82a6af093cb4888440`. Direct retrieval of its scenario source was denied. Its current PR body and the exact-#171-head strict-XPASS report support the merge instruction; future marker removal cannot yet be verified.
- Git inspection was denied, so base identity and checkout cleanliness were accepted from the brief. No tests, benchmarks, builds, real-server checks, or GitHub writes were performed.
- No code-quality or style review was conducted.

facts-b1: 49 claims checked, 9 findings (H/M/L: 0/1/8): CRLF wording; four round labels; ARTICLE title; HEAD size assurance; doc-location overclaim; attribution provenance
