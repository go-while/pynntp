# Council r2: fix/headerdict-copy (PR 7), hk-council-opus-c

Reviewed: delta `git show 8f63cdb` (head 8f63cdb, base upstream/main), and the whole
nntp/headerdict.py at 8f63cdb for context.
Score: **9/10**. Findings: 0 (H0/M0/L0).

## Open finding from r1

| Finding | Status |
|---|---|
| Low: `copy()` dropped `__slots__` values of a subclass | **Fixed.** nntp/headerdict.py:87-98 takes `object.__getstate__(self)` (the instance dict, `None` when it is empty, or a `(dict-or-None, slots)` tuple), updates the new `__dict__` and `setattr`s each slot, then gives the copy its own `_items`. That is the state `copy.copy()` used before the PR. Unset slots are left out by `object.__getstate__` (AttributeError is skipped), so they stay unset on the copy; a `None` dict part is skipped by the `isinstance(state, dict)` check. Mangled slot names come back mangled from `copyreg._slotnames`, so `setattr` hits the right descriptor. |

## New bugs from the delta

None found.

- `object.__getstate__` exists from Python 3.11, the minimum in pyproject.toml
  (`requires-python = ">=3.11"`); checked by a run on 3.11 (below).
- HeaderDict itself has no `__slots__`, so `dup.__dict__` always exists.
- deepcopy does not go through copy() (no `__deepcopy__`, no `__reduce__`), so it keeps
  the default reduce path, which already handled slots; the new test covers it.

## Notes (not findings)

- copy() reads the state with `object.__getstate__`, so a subclass that overrides
  `__getstate__` (to drop a cache, say) is copied with all its attributes, where
  `copy.copy()` before the PR went through the subclass's `__getstate__`. The copy is
  shallow, so the only effect is an extra shared reference; no input from a server or poster
  is involved. Worth a line in the docstring at most.

## Host verification

Host 118 (job 146), `git archive` copy of 8f63cdb: `pytest -q --ignore=tests/integration`
1044 passed; `ruff check`, `ruff format --check`, `mypy nntp tests` clean.
`uv run --python 3.11 ... pytest tests/test_headerdict.py`: 33 passed (includes the three
new slot tests).

## Not checked

Earlier commits of the PR (ee32d78, 3a216cf) beyond what the new code touches.
