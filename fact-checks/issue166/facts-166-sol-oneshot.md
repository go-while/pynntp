I’ll check only the changed lines and any contradictions they introduce. Shell access is denied in this run, so I can’t make the requested GitHub API calls; I’ll flag anything the local evidence cannot establish.
**3 findings: 0 High, 1 Med, 2 Low.** The remaining claims are supported by the supplied evidence.

Paths below are relative to ``. `merged` means `deep-int1/deep-int1-merged-hk-deep-dedupe.md`.

## Claims checked

| Claim | Verdict | Evidence |
|---|---|---|
| **C1:** Areas 1–8 received another complete review on November 17; increment each count once | **Shown.** | `deep-int1/brief.txt:1–5`; Sonnet explicitly lists every library file as read in `deep-int1/deep-int1-sonnet.md:3–6`; Sol confirms every library file in `deep-int1/deep-int1-sol-oneshot.md:170–174`. Date recorded in `upstream-gap/deep-fixes-status.md:72`. Previous counts were accepted as already checked. Separate legend contradiction below. |
| **C2:** All open PRs’ tests and CI were read with the merged code | **Shown for the PR changes**, not an exhaustive reread of every unchanged test. | The secondary scope is the test/CI **diff**, `deep-int1/brief.txt:5`. Sol reports reading that diff and checked-out tests/workflows, `deep-int1/deep-int1-sol-oneshot.md:170–174`. Other reviewers explicitly report narrower test coverage; they do not invalidate Sol’s coverage. |
| **C3:** Quadratic regex; approximately 64 KB costs approximately one CPU-minute; 65 s measured; poster-triggerable; #183 fixes it | **Shown.** | `council-facts-b1/facts-b1-hk-facts-b1.md:10,34–40`: 65,000 `a` bytes; `parse_keywords()` 63.47 CPU-seconds and `body()` 65.93; corresponding trailer path confirmed. The `article()` assertion follows the shared decoder path, not a separate timing measurement. |
| **C4:** Post-DEFLATE data accumulates quadratically and is silently discarded, including a second stream | **Shown.** | `merged:225–247`: successful two-stream XZHDR reproduction returns only the first stream; unchecked `unused_data` and quadratic concatenation documented. |
| **C5:** Mixed LF/CRLF rows merge and lose the next row; only the unterminated final row’s LF is refused | **Wrong as scoped.** Mixed-row loss is shown; refusal applies only to the XZ tail **with #171**, not plain XOVER/XHDR or unpatched 3.3.0. | `merged:95–125`. Local #171 checkout at `c337beb`: `worktree:hk-171/nntp/nntp.py:524–574`; plain reader: `worktree:deep-int1/nntp/nntp.py:555–564`. **F1 below.** |
| **C6:** Single-part decoding checks `=yend size`, not `=ybegin size` | **Shown.** | `merged:197–223`, including a successful mismatched-header-size reproduction. Also `nntp/nntp.py:1616–1623` and `nntp/yenc.py:89–94` in the supplied checkout. |
| **C7:** All PRs merged onto 3.3.0 pass the listed checks on November 17 | **Shown for successful check/suite results; not shown as every scenario/test passing.** | `upstream-gap/deep-fixes-status.md:65–72`: final `84f74ca`, 1,667 unit passes, **227 fault passes + 1 xfail**, **31 INN passes + 4 skips**. Ruff/format/mypy clean recorded at line 66. Local `integration-1` ref is `84f74cad…`. **F2 below.** |
| **C8:** Two combined-run interactions, fixed in #174 and #145 | **Shown in the historical evidence.** | `upstream-gap/deep-fixes-status.md:66` names both interactions and commits. `upstream-gap/council-pr174-kwonly-hk-council-opus-174k.md:15–18` verifies the positional-bool/FBT conflict. Local integration reflog lines 25–26 record merging `e339eda` and `3f61111`. |
| **C9:** Combined-diff and deep reviews found nothing above Low | **Shown as the final verified/triaged assessment**, not unanimous initial reviewer ratings. | Combined council: `upstream-gap/council-int1-r1-sol-oneshot.md:2–4` and `…hk-council-opus-int1.md:74–76`. Deep review: `merged:52–54,350–353` explicitly explains downgrading initial Med ratings after verification. |
| **C10:** The new accepted low-impact items are listed above | **Shown.** | `merged:341–348`: extend M7; add M2 and M6. These appear at `council-facts-166/issue166-new.md:60–62`. M10/M11 were classified as noise, not omitted accepted findings. |
| **C11:** New review statuses agree with the unchanged status-value definition | **Wrong: self-contradiction.** | `issue166-new.md:3` lists statuses only through `reviewed 3×`; changed lines 8–11 use `reviewed 4×`. **F3 below.** |

## Findings and exact corrections

### F1 — Med: Bare-LF rejection is attributed too broadly
At `issue166-new.md:61`, replace the bullet with:

> XZVER/XZHDR and plain XOVER/XHDR: a row ended by a bare LF followed by a CRLF row is read as one row, so the next row is lost (buggy server). With PR #171, XZVER/XZHDR reject a bare LF only in the unterminated tail after the last CRLF; this check does not apply to plain XOVER/XHDR.

### F2 — Low: “Pass” hides an expected failure and skipped tests
Replace the first sentence at `issue166-new.md:85` with:

> 2026-11-17: all open PRs merged together on 3.3.0 (branch `integration-1` on go-while/pynntp, head `84f74ca`) passed ruff and mypy --strict; the unit tests had 1667 passes, the fault-injection suite had 227 passes and one expected failure (#154), and the INN 2.7.3 integration suite had 31 passes and four skips (implicit TLS).

### F3 — Low: Review-count legend excludes the new value
Replace the first sentence at `issue166-new.md:3` with:

> Status values: not started, partial, in progress, reviewed (date), reviewed 2× (date), reviewed 3× (date), reviewed 4× (date).

No other contradiction with unchanged text was established.

## Not checked

Shell access was denied, so I could not fetch live issue #166, current PR heads, the remote integration branch, or GitHub commit messages. Historical claims above use the supplied reports, tracker, local source and local Git metadata. I did not independently rerun tests or timings.

facts-166: 11 claims checked, 3 findings (H/M/L 0/1/2): bare-LF rejection scope; expected failure/skips omitted; review-count legend contradiction
