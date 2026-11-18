# Council r2b: fix/reconnect-failure-broken @ 0ae1bd3 (hk-council-opus-d, Claude Opus 5.5)

Base upstream/main 2bfca17. Commits reviewed: 556aa09 and 0ae1bd3. I reviewed by reading only, with no host run, so I make no claim that tests pass.

## What I checked
- `_connect()` (nntp/nntp.py:310-339) at the head. `_broken = False` is now set only after `socket.create_connection()` returns (:321). `reconnect()` (:341-358) calls `close()` first, which sets `_broken = True`, so a failure in `create_connection` (OSError, timeout, or KeyboardInterrupt) leaves the client broken. The next command raises NNTPSyncError "call reconnect()" (:694) instead of EBADF from the old closed socket.
- Failures after the socket is open (TLS, greeting, STARTTLS, or in `NNTPClient._connect`: MODE READER or login) still go through `close()`, which sets broken. Unchanged.
- First connect from `__init__`: if `create_connection` raises, `_broken` is never set. The constructor raises, though, so no object reaches the caller, and there is no `__del__` that reads `_broken`. No harm.
- `__exit__` after a failed reconnect: `_broken` is True, so `close()` runs on the old socket, which has already been closed. That is idempotent and fine.
- `reconnect()` can be called again after a failure, and the test shows the second call works.
- Test `test_reconnect_socket_error_stays_broken`: it patches `create_connection` once to refuse and checks for NNTPSyncError and then a successful reconnect. On the base it fails, because `_broken` was False and the stale socket raised OSError. This matches the lead's check.

## Findings
None.

## Notes (not findings)
- The Raises section of `reconnect()` lists OSError and NNTPReplyError, as the constructor does. `NNTPClient._connect` can also raise NNTPProtocolError (data after the STARTTLS reply), NNTPError (connection closed during the greeting) or NNTPDataError (line too long). This gap is pre-existing in the constructor docstring as well. Optional: add "NNTPError: If the greeting or MODE READER exchange fails" to both.

## Not checked
- No host run.
- TLS handshake failure on reconnect, by test. By reading, it is covered by the existing `except BaseException: self.close()`.

## Score
9.6. The fix is minimal, the docstring states the failure contract, and the regression test covers the exact path.
