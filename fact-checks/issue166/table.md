### Open PRs and their review
Each PR was reviewed by two reviewers from different model families (Claude Opus plus OpenAI Sol or Terra), and every finding was fixed or decided before the PR was marked ready. The score line is in each PR's text.

| PR | Fixes | Council | State |
|---|---|---|---|
| #145 | tests | r2: opus 9.5, sol 9.5 | ready |
| #153 | CI | – (CI only; one review, 10/10) | ready |
| #167 | tests | r2: opus 9.5, sol 9.5 | ready |
| #168 | #162 | r1: opus 9.5, sol 9.5 | ready |
| #169 | #156 | r1: opus 9.5, sol 9.5 | ready |
| #170 | #159 | r2: opus 9.6, sol 9.5 | ready |
| #171 | #160 | r1: opus 9.5, sol 9.5 | ready |
| #172 | #163 | r1: opus 9.5, sol 9.5 | ready |
| #173 | #157 | r1: opus 9.5, sol 9.5 | ready |
| #174 | #158 | r1: opus 9.5, sol 9.5; keyword-only follow-up: opus 10, sol 9.5 | ready |
| #175 | #164 | r1: opus 9.5, sol 10 | ready |
| #176 | #165 | r1: opus 9.5, sol 10 | ready |
| #177 | lint config | r1: opus 9.5, sol 9.5 | ready |
| #178 | item 1 below | r2: opus 9.6, sol 10 | ready |
| #179 | item 2 | r2: opus 9.5, sol 10 | ready |
| #180 | item 4 | r2: opus 9.6, sol 10 | ready |
| #181 | item 5 | r2: opus 9.6, sol 10 | ready |
| #182 | item 3 | r1: opus 9.6, sol 10 (round 0: haiku 9, sonnet 9) | ready |
| #183 | item 6 | r2: opus 9.6, sol 10 | ready |
| #184 | item 7 | r2: opus 9.5, sol 10 | ready |
| #185 | item 8 | r2: opus 9.5, sol 10 | ready |
| #186 | item 9 | r2: opus 9.5, terra 9.5 | ready |
| #187 | #161 | r2: opus 9.5, terra 9.5 | draft (held back: low impact, touches every command) |

All of them merged together (branch `integration-1` on go-while/pynntp): combined-diff review r1: opus 9.6, sol 9.5; deep review of all of `nntp/` (Haiku, Sonnet, Terra, Sol, merged by Opus): nothing above low impact.

