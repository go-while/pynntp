# Council R2, PR 7 fix/headerdict-copy (reviewer hk-council-sonnet)

Read: `git show 8f63cdb` and nntp/headerdict.py at that commit in full (no __slots__, __getstate__ or __reduce__ on HeaderDict; _from_fields also sets _items; requires-python >= 3.11, so object.__getstate__ exists).
Host run (120): tree of 8f63cdb, pytest without integration: 1044 passed; mypy: no issues; ruff check and format --check: clean.

## Open finding
- Low (copy() dropped __slots__ values of a subclass that a plain copy.copy() kept before the PR): fixed. copy() now takes object.__getstate__(self): a dict, None, or a (dict, slots) tuple. The isinstance checks cover all three (None when there is no instance state, which cannot happen here since _items is always in __dict__ because HeaderDict has no __slots__). Slots are set with setattr, as copy's own _reconstruct does; unset slots are absent from the slots dict, so they stay unset (test_copy_with_unset_slots). Private mangled slot names work (the state uses the mangled names). `dup._items` is replaced by a fresh dict copy after the state update, so the copy stays independent. copy.copy() goes through __copy__ -> copy(); deepcopy has no __deepcopy__ and uses __reduce_ex__, which already handled slots; the new test covers all three and shows deepcopy slot values stay independent.

## New bugs in the delta
Nothing found. Checked: a subclass that defines its own __getstate__ is ignored by copy() as before (the old code also ignored it, since __copy__ called the old copy()), so no regression; a subclass with a custom __setattr__ sees the same setattr calls copy.copy would make; the state dict is shallow-copied into dup.__dict__ (never shared). Python 3.11 minimum matches the pyproject, so object.__getstate__ is available.

Score: 9/10. 0 findings (0/0/0).
