# pynntp council reports

Review reports behind the "council" score lines in the go-while PRs to greenbender/pynntp and in the table of greenbender/pynntp#166. Each PR was reviewed by reviewers from two model families (Claude Opus plus OpenAI Sol or Terra) in rounds until every finding was fixed or decided; round 0 (Haiku, Sonnet, Luna) came before the council for the newer PRs.

| Folder | What |
|---|---|
| `councils/` | one report per reviewer and round. Older PRs: `council-pr<N>-r<round>-<reviewer>.md` (#145, #167-#177); newer PRs: `council-fix-<branch>-r1|r2|r2b-<reviewer>.md` (#178-#187 and follow-ups; "r2b" is the second round for that batch). `council-int1-*`: review of the combined diff of all open PRs (branch `integration-1`) |
| `round0/` | round-0 reviews and their cross-checks |
| `deep-int1/` | full deep review of `nntp/` on `integration-1`: four reviewers (Haiku, Sonnet, Terra, Sol) and the merged, verified result (`deep-int1-merged-*`) |
| `fact-checks/` | fact checks of public texts: the batch-1 PR texts and the #166 update |
| `briefs/` | the briefs some councils worked from |

The round label in a PR's score line counts that PR's own council rounds, so it can differ from the batch round in a file name. Local paths, test-host addresses and internal tool names are replaced with neutral words. Reviews by reading never claim that tests passed; test results are in the commit messages and in #166.
