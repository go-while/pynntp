# Council r2b: fix/yenc-error-pickle @ a0e15a7 (hk-council-opus-d, Claude Opus 5.5)

Base upstream/main 2bfca17. Commits reviewed: f762729 and a0e15a7. I reviewed by reading only, with no host run, so I make no claim that tests pass.

## What I checked
- `NNTPYEncError.__reduce__` (nntp/nntp.py:249-255) returns `(type(self), (message, data), self.__dict__)`, the same shape as `BaseException.__reduce__`, which also returns the live `__dict__`.
  - Pickle: `data` appears both in the args and in `__dict__`, but pickle memoizes the same object, so it is not stored twice. `__setstate__` (from BaseException) restores notes and extra attributes.
  - `copy.copy`: the clone shares the `__notes__` list, which is normal shallow-copy behaviour and matches BaseException. `deepcopy` deep-copies the state.
  - `object.__reduce_ex__` calls an overridden `__reduce__`, so copy and pickle both use it.
  - With empty args the message falls back to `""`, which round-trips.
  - `type(self)` keeps subclasses that share the constructor signature.
- Other exception classes: NNTPReplyError has args `(code, message)` that match `__init__`, and the rest take one message, so all of them round-trip with BaseException's default. The new test covers every exported error class, including a note, an extra attribute, pickle, copy and deepcopy.
- `str()`, `args` and the constructor are unchanged.

## Findings
None.

## Notes (not findings)
- Traceback, `__cause__` and `__context__` are not pickled. That is the same as every Python exception, so nothing to do.

## Not checked
- No host run.
- Pickle protocols other than the default, by test. By reading, `__reduce__` does not depend on the protocol.

## Score
9.6. The fix is correct and minimal, it matches BaseException's semantics, and the test is broad.
