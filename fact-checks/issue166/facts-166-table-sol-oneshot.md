The live PRs match all 23 listed states and “Fixes” mappings. The header has two exceptions: #153 had one reviewer, and neither #153 nor #177 has a score line in its PR text. I’m checking the report scores and finding dispositions next.
There’s also a timing counterexample to the header: #171 was marked ready at 16:08 UTC on November 17, but a wording finding from the deep review was fixed at 20:47–20:48 UTC. All listed council scores match the reports; the deep-review result is supported after Opus’s verification and severity triage.
**78 claims checked: 3 findings—2 Medium, 1 Low.** All 23 “Fixes” mappings, council entries and live states are supported.

## Findings

### 1. Medium — “Each PR” had two model-family reviewers: **wrong**

The header contradicts its own #153 row. That CI-only PR had one Sonnet review, scored 10/10—not Opus plus OpenAI.

Evidence: `/claude/projects/pynntp/pynntp-tools/upstream-gap/review-pr153-hk-testprs.md:1–20`; `deep-fixes-status.md:57–59`. The other 22 PRs have paired Opus/OpenAI reports.

**Exact corrected wording:**
> Each PR except #153 was reviewed by Claude Opus plus OpenAI Sol or Terra. #153, which changes CI only, had one Sonnet review.

### 2. Medium — Every finding was fixed or decided before readiness: **wrong**

#171 supplies a concrete counterexample:

- GitHub’s live timeline records `ready_for_review` at **2026-11-17 16:08:06 UTC**.
- The deep-review merge report identifies its overbroad bare-LF wording as a finding requiring correction: `/claude/projects/pynntp/pynntp-tools/deep-int1/deep-int1-merged-hk-deep-dedupe.md:95–125,338–339`.
- Fix commits `d55abda` and `c337beb` are dated **20:47:21** and **20:48:10 UTC**, respectively—after readiness. Their commit messages explicitly identify the deep-review wording correction.

**Exact corrected wording:**
> The table gives the latest recorded review scores; it does not establish that every finding was fixed or decided before readiness. #171 received a further wording fix after it was marked ready.

### 3. Low — Every PR text contains its score line: **wrong**

The live bodies of **#153 and #177 contain no council score line**. Their table entries are nevertheless supported by the reports.

Evidence: live `gh pr view` results; `review-pr153-hk-testprs.md:20`; `council-pr177-r1-hk-council-opus-177.md:75–82`; `council-pr177-r1-sol-oneshot.md:3–5,19`.

**Exact corrected wording:**
> Score lines are in the PR text except for #153 and #177; their table entries come from the review reports.

## T1–T3: every PR

All report paths below are relative to `/claude/projects/pynntp/pynntp-tools/upstream-gap/`. Each wildcard identifies the paired reviewer reports.

“Shown” in the Council column means both the table-to-PR-text comparison and the PR-text-to-report comparison passed, using the specified report-only exceptions.

| PR | T1: Fixes | T2: Council | T3: live state | Report evidence |
|---|---|---|---|---|
| #145 | **Shown:** tests | **Shown:** r2 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr145-r2-*` |
| #153 | **Shown:** CI | **Shown:** one review, 10/10 | **Shown:** ready | `review-pr153-hk-testprs.md` |
| #167 | **Shown:** tests | **Shown:** r2 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr167-r2-*` |
| #168 | **Shown:** #162 | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr168-r1-*` |
| #169 | **Shown:** #156 | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr169-r1-*` |
| #170 | **Shown:** #159 | **Shown:** r2 Opus 9.6, Sol 9.5 | **Shown:** ready | `council-pr170-r2-*` |
| #171 | **Shown:** #160 | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr171-r1-*` |
| #172 | **Shown:** #163 | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr172-r1-*` |
| #173 | **Shown:** #157 | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr173-r1-*` |
| #174 | **Shown:** #158 | **Shown:** r1 Opus 9.5, Sol 9.5; follow-up Opus 10, Sol 9.5 | **Shown:** ready | `council-pr174-r1-*`, `council-pr174-kwonly-*` |
| #175 | **Shown:** #164 | **Shown:** r1 Opus 9.5, Sol 10 | **Shown:** ready | `council-pr175-r1-*` |
| #176 | **Shown:** #165 | **Shown:** r1 Opus 9.5, Sol 10 | **Shown:** ready | `council-pr176-r1-*` |
| #177 | **Shown:** lint config | **Shown:** r1 Opus 9.5, Sol 9.5 | **Shown:** ready | `council-pr177-r1-*` |
| #178 | **Shown:** item 1 | **Shown:** r2 Opus 9.6, Sol 10 | **Shown:** ready | `council-fix-yenc-unclosed-block-r2b-*` |
| #179 | **Shown:** item 2 | **Shown:** r2 Opus 9.5, Sol 10 | **Shown:** ready | `council-fix-empty-message-id-r2b-*` |
| #180 | **Shown:** item 4 | **Shown:** r2 Opus 9.6, Sol 10 | **Shown:** ready | `council-fix-reconnect-failure-broken-r2b-*` |
| #181 | **Shown:** item 5 | **Shown:** r2 Opus 9.6, Sol 10 | **Shown:** ready | `council-fix-yenc-error-pickle-r2b-*` |
| #182 | **Shown:** item 3 | **Shown:** r1 Opus 9.6, Sol 10; round 0 Haiku 9, Sonnet 9 | **Shown:** ready | `council-fix-post-body-item-lines-r2b-*`, `round0-post-body-item-lines-*` |
| #183 | **Shown:** item 6 | **Shown:** r2 Opus 9.6, Sol 10 | **Shown:** ready | `council-fix-yenc-keyword-regex-r2b-*` |
| #184 | **Shown:** item 7 | **Shown:** r2 Opus 9.5, Sol 10 | **Shown:** ready | `council-fix-headerdict-copy-r2b-*` |
| #185 | **Shown:** item 8 | **Shown:** r2 Opus 9.5, Sol 10 | **Shown:** ready | `council-fix-head-read-all-r2b-*` |
| #186 | **Shown:** item 9 | **Shown:** r2 Opus 9.5, Terra 9.5 | **Shown:** ready | `council-fix-ssl-context-plaintext-r2b-*` |
| #187 | **Shown:** #161 | **Shown:** r2 Opus 9.5, Terra 9.5 | **Shown:** draft | `council-fix-161-unread-data-r2b-*` |

Additional evidence:

- **Fixes:** every live PR body was read; linked issues #156–#165 were checked through GitHub’s API. Item references match `issue166-new2.md:68–80`.
- **Round labels:** the newer reports’ `r2b` labels versus public `r2`, and #182’s public `r1`, are acceptable under the stated PR-local counting convention. The tracker documents the split and rounds at `deep-fixes-status.md:46–49,71`.
- **States and count:** live `gh pr list --state open` returned exactly these **23 PRs**, with only #187 draft.
- **#187’s hold-back reason — shown:** `three-questions-2026-11-17.md:28` explicitly records low problem severity, high later risk, checking every command, and keeping it draft. The live PR body also describes the every-command check.

## T4–T5 and remaining claims

| Claim | Verdict and evidence |
|---|---|
| All PRs had Opus plus OpenAI review | **Wrong:** finding 1. Supported for all except #153. |
| Every finding resolved before readiness | **Wrong:** finding 2. |
| Score line in every PR body | **Wrong:** finding 3. |
| All 23 merged on fork branch `integration-1` | **Shown:** `deep-fixes-status.md:65–72`; deep merged report `:3`; combined-review merge checks at `council-int1-r1-hk-council-opus-int1.md:20–26`. Live branch head is `84f74cad154c02bcc047bb99e746bb49d0a2a5e9`. |
| Combined-diff r1: Opus 9.6, Sol 9.5 | **Shown:** `council-int1-r1-hk-council-opus-int1.md:120–128`; `council-int1-r1-sol-oneshot.md:2,17`. This review covered combined `nntp/` interactions, not every test/CI change. |
| Deep review covered all `nntp/`, with Haiku, Sonnet, Terra, Sol, merged by Opus | **Shown:** deep-review reports’ scope statements; merged report `:3–8`; tracker `:72`. |
| Deep review found nothing above low impact | **Shown as the merged, verified conclusion:** merged report `:38–54,350–353`. Individual reviewers initially reported Medium findings; Opus’s verification/triage reduced them to Low. It is not a claim of unanimous original Low ratings. |

## Limits and counting

I did not rerun tests, reproduce behaviours, independently reconstruct the integration ancestry, or establish resolution timestamps for every finding. Those limits do not affect the score/state comparisons or the demonstrated #171 timing counterexample.

Count: 69 row claims, one PR-count claim, #187’s reason, three header claims, and four closing-line claims.

facts-166-table: 78 claims checked, 3 findings (H/M/L: 0/2/1): #153 reviewer exception; readiness chronology; missing PR score lines
