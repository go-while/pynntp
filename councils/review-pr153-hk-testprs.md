# Review of #153 port/inn2-python, head 1e22c34 (base upstream/main 2bfca17), by hk-testprs

Change: .github/workflows/check.yml, job test-inn2: `python-version: "3.14"` becomes `"3.15"  # The newest CPython, as in the test matrix`. One line; nothing else differs from upstream/main (git diff upstream/main...origin/port/inn2-python).

## Findings
None.

## Notes
- "3.15" is in the matrix of the same file (["3.11" ... "3.15", "3.15t"]), so setup-uv resolves it the same way there; the comment is true (3.15 is the newest entry; 3.15t is the same version).
- No other file mentions the Python used by test-inn2 (grep for "3.14"/"test-inn2" in *.md and tests/integration: only the matrix and a pyproject classifier for 3.14; the classifier list has no 3.15 and is not part of this change).
- The job's `uv sync --locked` runs on 3.15 then; uv.lock resolves for requires-python, same as the matrix job's 3.15 leg.

## Host results (10.10.11.116, Ubuntu 24.04, Python 3.12.3, job 262)
uv sync --locked ok; ruff check: All checks passed; ruff format --check: 31 files already formatted; mypy --strict .: no issues in 26 source files; pytest -q -p no:cacheprovider --ignore=tests/integration: 1034 passed. The change is a workflow line, so these only show that the tree is as green as base.

## Not checked
- The test-inn2 job itself (needs ubuntu-26.04 runner, sudo setup.sh and INN 2.7.4); i.e. whether the integration tests pass on CPython 3.15 there. Only a CI run on the PR shows that.
- Python 3.15 locally on a host (no unit run on 3.15 by me).

Score: 10/10, 0 findings.
