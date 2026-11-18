# Council r2: fix/header-dot-stuffing (PR 5), hk-council-opus-c

Reviewed: delta `git show 71edde9` (head 71edde9, base upstream/main), plus
`_prepare_article`, `post()`, `ihave()` and `utils.unparse_headers` at 71edde9 for context.
Score: **9/10**. Findings: 0 (H0/M0/L0).

## Open finding from r1

| Finding | Status |
|---|---|
| Low: CR/NUL error said "Body line" although header lines pass the same check | **Fixed.** nntp/nntp.py:1929 now says "Article line contains a CR outside a CRLF ending, or a NUL"; the docstrings of post() (1816), ihave() (1855) and _prepare_article (1910) say "a line of the article (header or body)". `git grep -i "body line"` at 71edde9 finds no stale wording left (only the unrelated `_SEND_SIZE` comment). Tests (tests/test_posting.py:63-65, 85-87) match the new text. |

## New bugs from the delta

None. The delta changes only a message string, docstrings and two test `match=` patterns.

## Notes (not findings)

- In practice a header line never reaches the NNTPDataError check: `utils.unparse_headers`
  (nntp/utils.py:239) already raises ValueError for NUL or a CR/LF outside a fold, and
  post()/ihave() call it first. "header or body" in the docstrings is therefore broader
  than what can happen, but not wrong, and the ValueError is documented next to it.

## Host verification

Host 118 (job 146), `git archive` copy of 71edde9: `pytest -q --ignore=tests/integration`
1073 passed; `ruff check`, `ruff format --check`, `mypy nntp tests` clean.

## Not checked

The rest of the PR (dot-stuffing, LF splitting of body items) was reviewed in r1 and is not
part of this delta; no INN integration run.
