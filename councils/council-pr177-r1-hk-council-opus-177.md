# Council review, PR #177 "Simplify ruff lint configuration", round 1

Reviewer: hk-council-opus-177 (Claude Opus, fresh). Rules rev 3.22 (HASH.md OK).
Head f8b978d (local branch pr-177), base upstream/main 2bfca17. Diff: pyproject.toml only.

## What I did

- Read the diff, the full head pyproject.toml, .pre-commit-config.yaml (ruff-pre-commit
  v0.17.4: ruff-check, then ruff-format), .github/workflows/check.yml (runs mypy and pytest,
  no ruff), and uv.lock (ruff 0.17.4, the same version as pre-commit). Grepped the repo for
  TODO/FIXME/XXX/HACK (none), print( (none) and noqa comments.
- Ran ruff only, on test host 10.10.11.117 through jobq.sh (vm-run.sh jobs 307 and 308),
  using a scratch copy of pr-177 and ruff 0.17.4 from uv.lock:
  - head: `ruff check .` passes; `ruff format --check .` reports 31 files already formatted and
    no "may cause conflicts with the formatter" warning; `ruff check --select ISC001 --diff .`
    shows nothing.
  - base config (2bfca17 pyproject.toml): check and format --check pass too.
  - Rules each config enables, from `--show-settings`: base 735, head 754. **No rule enabled on
    the base is missing on the head.** Rules the head adds: COM818, COM819, FAST001-003,
    FBT001-003, FIX002, ISC001, T201, T203, TD001-TD007.
  - ISC001 compared with the formatter on a probe file: ruff format 0.17.4 joins implicit
    concatenations that fit on one line ("a" "b" becomes "ab", including inside a call). After
    that, ISC001/ISC002/ISC003 report nothing, `--fix` changes nothing, and format --check is
    clean. The two do not conflict in this version.
  - With the per-file ignores turned off, FBT reports 17 hits: 9 in nntp/nntp.py (FBT001/FBT002
    at 567, 613, 1398, 1477, 1541, 1763) and 8 FBT001 in tests. There are no FBT003 hits.
  - TD, FIX, T20, COM818/819 and FAST report 0 hits on the whole repo.
  - `--preview --statistics` shows which preview rules would be enabled once they become
    stable (used for finding 1).

## Findings

| # | Where (head) | What goes wrong and when | Sev | Confirmed |
|---|---|---|---|---|
| 1 | pyproject.toml:54 `select = ["ALL"]` together with the ignore list at 55-62 | ALL turns on every rule family ruff marks stable, including families the old list left out on purpose (DOC was commented out). Today the pydoclint DOC rules are preview-only, so they are off. On the head they would already report 122 errors (DOC201 57, DOC502 33, DOC403 14, DOC501 12, DOC402 6). Ignoring "D" does not cover "DOC". When a future ruff makes DOC stable, the quarterly pre-commit.ci autoupdate PR (and main once that PR is merged) fails with about 122 errors. Under the old list, only new rules inside families already selected (RUF, PL, UP ...) could appear; whole new families could not. Fix: add "DOC" to `ignore`, or accept the risk and handle it when the autoupdate PR fails. The failure is loud, never silent. | Low | Run on host (preview counts); the stabilisation is a forecast |

No other findings. Specifically:
- Lost coverage: none. The head enables a strict superset of the base's rules (735 of 735 kept).
  The old `TCH` alias is replaced by `TC`, which ALL includes.
- ISC001 and `ruff format`: no conflict in ruff 0.17.4. I checked by running both, and ruff
  printed no warning. pre-commit.ci runs both hooks; check.yml runs neither.
- FIX002 dropped from ignore: the repo has no TODO/FIXME comments today, so nothing fails (0 hits).
- Deprecated, removed or preview rules: ALL selects none of them without `preview = true`, and
  the head run printed no warnings. CPY001 is in the ignore list, which is harmless.

## Notes (not findings)

- Policy change: any new `TODO`/`FIXME`/`XXX` comment now fails three ways: FIX002/FIX001/FIX003,
  plus TD002 (missing author) and TD003 (missing issue link). Contributors will need
  `# TODO(name): ... <issue link>` or a noqa. Also, T201 (print) is now enforced everywhere,
  docs/ included.
- `"nntp/nntp.py" = [..., "FBT"]` (pyproject.toml:72) is wider than needed. All 9 hits are
  FBT001/FBT002 on 6 existing public signatures (`info`/`_info` yz, `_read_body`/`article`/`body`
  decode, `xfeature_compress_gzip` terminator), and FBT003 has 0 hits. Possible alternatives:
  `["FBT001", "FBT002"]`, or noqa on the 6 lines so that a new boolean-trap API added to
  nntp.py still gets flagged. This is no regression, because FBT was not checked anywhere before.
- `"tests/*" = ["FBT001", ...]` (line 73) is narrow. FBT002/FBT003 stay on in tests with 0 hits.
  A future test that passes a bool positionally to an API (e.g. `client.info(c, m, True)`)
  would need a keyword argument, which is arguably better anyway.
- ALL also auto-enables any brand-new rule family added in a later ruff release. This is the
  general form of finding 1, and ruff's docs warn about it. A pinned rev and uv.lock keep CI
  stable until the next upgrade.
- uv.lock (0.17.4) and the pre-commit rev (v0.17.4) agree today. pre-commit.ci's quarterly
  autoupdate moves only the rev, so a local `uv run ruff` and pre-commit.ci can drift apart.
  This predates the PR.

## Not checked

- Behaviour of ruff releases newer than 0.17.4 (finding 1 uses today's preview set as a proxy).
- The real pre-commit.ci run, and the other open PRs against this config (given as known facts).
- Whether `--config` resolving per-file-ignore globs from cwd affected the base check run. It
  does not affect the enabled-rule comparison, which reads the global rule set.
- mypy and pytest: unaffected by a ruff-only change, and not run.

## Score

9.5. The change keeps every rule the base enforced and adds 19 more. The pinned ruff runs
check and format without conflict, and the repo passes. The only finding is Low: a predictable
break on a future upgrade, which is loud and fixed in one line. Adding "DOC" to `ignore` would
remove it.

#177: 9.5, 1 findings (0/0/1): ALL will enable DOC (122 hits today in preview) when ruff stabilises it
