# Council r2b: PR 7 fix/headerdict-copy @ 8f63cdb (reviewer hk-council-opus-e, Claude Opus 5.5)

Base upstream/main 2bfca17. Reviewed by reading only (diff of the 3 commits, full
nntp/headerdict.py at head, pyproject/CI matrix). No host run; I claim no test results.

## Findings

Nothing found.

## What I checked

- The bug on the base: no `__copy__`, so `copy.copy()` goes through `__reduce_ex__(4)` and
  `copy._reconstruct(deep=False)` does `y.__dict__.update(state)`: the copy shares `_items`. And
  HeaderDict had no `copy()` (MutableMapping does not give one), so `head()` results could not be
  copied like a dict.
- `copy()` at head: `type(self).__new__`, then the state from `object.__getstate__` (dict, or
  `(dict, slots)` tuple, or None when the dict is empty; HeaderDict always has `_items`, so the dict
  branch runs), slot values set with `setattr` (copyreg's slot names are already mangled and skip
  `__dict__`/`__weakref__`, unset slots are left out), then a fresh `_items` dict. Values are tuples
  of str, so a shallow `dict.copy()` is fully independent.
- Python versions: `typing.Self` and `object.__getstate__` need 3.11; requires-python is >=3.11 and
  the CI matrix starts at 3.11. OK.
- deepcopy and pickle are unchanged (no `__deepcopy__`/`__reduce__`), and the tests pin both,
  including subclasses and `__slots__`.
- Tests cover module copy, method copy, both directions of independence, name case and order,
  subclass type and instance attributes, slot values (set, unset, deepcopy independence).

## Notes (not findings)

- A subclass that defines its own `__getstate__`/`__setstate__` is bypassed by `copy()` (it calls
  `object.__getstate__` directly), and `copy.copy()` now goes through `copy()`. Only matters for
  user subclasses with custom pickling state; the docstring describes what is copied.
- Style: nntp.py imports `Self` under `TYPE_CHECKING`; headerdict.py imports it at run time. Both
  work with `from __future__ import annotations`.

## Not checked

- No host run. HeaderDict subclasses with a custom `__new__` that needs arguments.

Score: 9.5
