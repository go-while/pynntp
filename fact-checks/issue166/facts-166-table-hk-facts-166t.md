# Fact check: #166 section "Open PRs and their review" (hk-facts-166t, 2026-11-18)

Scope: table.md only. Evidence: live `gh pr view` / `gh api` GETs on greenbender/pynntp (PRs, issues #156-#165, timelines of #145/#153/#167/#171/#177, #177 files and comments), reports in upstream-gap/ (council-pr*, council-fix-*, round0-post-body-item-lines-*, council-int1-r1-*, review-pr153-hk-testprs.md, deep-fixes-status.md, three-questions-2026-11-17.md), deep-int1/deep-int1-merged-hk-deep-dedupe.md, issue166-new2.md. Nothing was run.

## T1 Fixes cells: shown (23/23)
- #168-#176 and #187: each PR body says "Fixes #N" with the same number (#162, #156, #159, #160, #163, #157, #158, #164, #165, #161). The live issue titles match the PR titles.
- #178-#186: the issue's numbered list names "PR #N" for items 1-9 exactly as in the table (178=1, 179=2, 182=3, 180=4, 181=5, 183=6, 184=7, 185=8, 186=9). The PR titles and bodies match the items. The list comes after the table, so "item 1 below" is right.
- #145 (fault-injection tests), #167 (integration tests), #153 (CI workflow, one line), #177 (ruff config, cclauss): shown.
- Note: #172 also carries item 10 (linear unfolding; the list says "follow-up in #172", and the PR body says so). The cell is not wrong, only incomplete. See L3.

## T2 Council cells: shown (23/23)
Each cell matches the PR's own score line word for word. Checked against the reports:
- #145 r2 opus 9.5 / sol 9.5 (council-pr145-r2-*); #167 r2 9.5 / 9.5 (council-pr167-r2-*).
- #168, #169, #171, #172, #173, #174 r1 9.5 / 9.5; #175, #176 r1 9.5 / 10; #170 r2 9.6 / 9.5; #174 kwonly 10 / 9.5 (council-pr174-kwonly-*).
- #177 r1 opus 9.5, sol 9.5 (council-pr177-r1-*). #153 10/10 (review-pr153-hk-testprs.md, one reviewer, Sonnet per tracker line 59).
- #178 9.6/10, #179 9.5/10, #180 9.6/10, #181 9.6/10, #182 9.6/10, #183 9.6/10, #184 9.5/10, #185 9.5/10 (the council-fix-*-r2b-* Opus and sol-low reports). #186 and #187 9.5 / terra 9.5 (r2b terra-high).
- #182 round 0: haiku 9, sonnet 9 (round0-post-body-item-lines-*). Its reports are named r2b, but the PR's own first council round is r1. Per the brief and the tracker (Rev 3.47, "each PR counts its own rounds") this is not a finding. Likewise "r2" in #178-#187 means the r2b re-run. #184 and #186 also had an intermediate r2 with Sonnet in Sol's seat (tracker line 45); the published scores are the final r2b ones.

## T3 State: shown (23/23 + reason)
- Live: 22 PRs are open with isDraft=false; #187 is open with isDraft=true.
- The reason for #187 is shown in three-questions-2026-11-17.md: "low: buggy/hostile server only" and "touches every command", "hold back (weak 1, high 2)".

## T4 Header: partly wrong / self-contradicting
- "two reviewers from different model families (Claude Opus plus OpenAI Sol or Terra)": shown for 22 PRs (reports exist for each). **Wrong for #153**: it had one review, by a Sonnet reviewer, and the table row itself says "one review". See L1.
- "every finding was fixed or decided before the PR was marked ready": shown for the council findings of our own PRs. Two exceptions:
  - #177 is cclauss's PR and was never a draft (opened 2026-11-13; no convert_to_draft or ready_for_review events). Our one Low finding (DOC rules under `select = ["ALL"]`) went to him as a suggestion on 11-16 and is not applied in the diff.
  - #171 was marked ready on 2026-11-17 at 16:08Z. The deep-review wording fix (d55abda, c337beb) was committed at 20:47Z, after that. That was a deep-review finding, not a council finding.
  See L2.
- "The score line is in each PR's text": **wrong for #153 and #177**. Neither body contains a score line (grep for council/score/opus: 0 hits). See L1.

## T5 Closing line: shown
- Branch integration-1 = upstream/main 2bfca17 + all 23 open PRs (tracker line 65; deep-dedupe header "23 open PRs"). The Opus int1 report says "19 PRs" because it reviewed the combined nntp/ diff; that is consistent.
- Combined-diff r1: opus 9.6 (council-int1-r1-hk-council-opus-int1.md), sol 9.5 (council-int1-r1-sol-oneshot.md). Shown.
- Deep review: four reports, T=Terra, L=Sol, S=Sonnet, H=Haiku, merged by hk-deep-dedupe (Opus per tracker line 72). The verdict "No High or Med item survives verification" is shown. Note: several individual reviewers rated items Med (S1, H1, T1, T2, L1-L4). "Nothing above low impact" is the merged, verified verdict, so this is not a finding.

## Findings

| # | Sev | Claim | Problem | Corrected wording |
|---|---|---|---|---|
| L1 | Low | Header: "Each PR was reviewed by two reviewers ... The score line is in each PR's text." | #153 had one (Sonnet) review, and the table row says so (self-contradiction). #153 and #177 have no score line in their text. | "Each PR was reviewed by two reviewers from different model families (Claude Opus plus OpenAI Sol or Terra), except #153 (a one-line CI change: one review). The score line is in each PR's text, except #153 and #177 (cclauss's PR), whose scores are from our review reports." |
| L2 | Low | Header: "every finding was fixed or decided before the PR was marked ready" | It does not fit #177 (cclauss's, never a draft; our Low finding was sent as a suggestion). It also does not fit the later deep-review wording fix on #171, which was committed after #171 was ready. | "and every council finding was fixed or decided before we marked our PR ready (#177 is cclauss's PR: our one Low finding went to him as a suggestion)." |
| L3 | Low (optional) | Row #172: Fixes "#163", Council "r1: opus 9.5, sol 9.5" | #172 also fixes item 10 (quadratic unfolding). That follow-up had its own council (council-fix-163-header-unfold-r1: opus 10, sol 10), which is not in the PR's score line, unlike #174's follow-up. | Fixes "#163, item 10"; Council "r1: opus 9.5, sol 9.5; unfolding follow-up: opus 10, sol 10". The PR text needs the same score line first. Or keep the row as it is; it is not wrong. |

## Could not check
- Whether each score still applies to the current PR head. Later commits after a council round include #145 (nntp-testkit v0.14.1, 3f61111 / f789662), #171 (d55abda, c337beb) and #172 (6416b2c). The tracker says these were re-checked or wording-only.
- The reviewers' model identity, beyond the reports' own headers and the tracker.

facts-166-table: 78 claims checked, 3 findings (H/M/L 0/0/3): #153 one review and #153/#177 no score line vs header; "fixed before marked ready" vs #177/#171; #172 item 10 + follow-up score (optional)
