# Changelog

## 3.0.0 (unreleased candidate)

The first release of the maintained fork. It fixes the protocol bugs found in
the October 2026 review (see REVIEW.md, which lists each finding with the
commit that fixed it). Several fixes change behaviour, so read the "Changed"
section before upgrading.

### Changed (may need changes in your code)

- **Python 3.10 or newer is required** (3.9 reached end of life in October 2025).
- **LIST ACTIVE and NEWGROUPS return the right water marks.** They read the
  server's `name high low status` order; before, `low` and `high` were
  swapped. `Newsgroup(name, low, high, status)` is unchanged, so remove any
  workaround that swaps the two values.
- **Commands are sent at call time.** Methods that return an iterator
  (`list_active()`, `xover()`, `capabilities()`, …) now send their command and
  read its status when called, not on the first iteration; errors from the
  status line are raised at the call. Replies are still streamed.
- **One reply at a time.** A returned reply that is still held, unread or
  partly read, makes the next command raise `NNTPSyncError` until the reply is
  read to its end, closed with `close()` or dropped. Leaving a `for` loop over
  it early is fine: the rest of the reply is read and dropped before the next
  command.
- **yEnc bodies are checked.** `body()` and `article()` check decoded yEnc data
  against the size and CRC (`pcrc32`, or `crc32` for single-part posts) of its
  `=yend` trailer, and raise `NNTPDataError` on a mismatch or a missing trailer
  instead of returning corrupt data.
- **POST checks the whole article first.** `post()` prepares and validates the
  entire article before sending anything (iterable bodies are consumed up
  front; above 1 MiB through a temporary file). NUL or bare CR in the body
  raises `NNTPDataError` and nothing is posted; before, a truncated article
  was posted.
- **CR/LF/NUL are rejected** with `ValueError` in header names and values and
  in command arguments and credentials, before anything is sent.
- **Error types.** Timeouts raise `NNTPTimeoutError` (an `NNTPError` and a
  `TimeoutError`) and close the connection; header, DATE and newsgroup parse
  errors raise `NNTPDataError` instead of `ValueError`; a closed connection
  raises `NNTPError`.
- **`PYNNTP_TLS_INSECURE`** turns certificate checks off only for `1`, `true`,
  `yes` or `on`; before, any value (even `0`) did.
- **STARTTLS** sends MODE READER before TLS (RFC 4642) and never sends AUTHINFO
  before TLS is up.
- **MODE READER after authentication** is not sent again (RFC 4643): if the
  server answers MODE READER with 480, the client logs in and `mode_reader()`
  returns `False` (posting status unknown).
- **LIST EXTENSIONS** is documented as obsolete; use `capabilities()`.
- The `__main__` demo at the end of `nntp/nntp.py` is removed.
- Package metadata uses PEP 621; the project URLs point to the maintained fork.

### Added

- `stat()`, `listgroup()` and `over()` (RFC 3977; #43, #45, #46).
- `ihave()` (#42).
- `login()`: explicit AUTHINFO USER/PASS with given or stored credentials.
- `ssl_context` argument for both client classes.
- `NNTPSyncError` and `NNTPTimeoutError` are exported.
- `py.typed`: type checkers use the package's annotations.
- Reply iterators have a `close()` that drops the rest of the reply at once.
- The sdist contains the tests (#74); the integration tests run only with
  `PYNNTP_INTEGRATION=1`, so `pytest` works without a news server (#56).

### Fixed

- Lines starting with a dot were returned twice, once unstuffed and once raw,
  by BODY, ARTICLE, HEAD, LIST and the other multi-line commands; this
  corrupted yEnc bodies (#99).
- NEWGROUPS and NEWNEWS sent `UTC` instead of `GMT`, which INN rejects with 501.
- HDR expected code 221 instead of RFC 3977's 225.
- Leaving a reply early (`break`, a single `next()`, an exception or a parse
  error) locked the client up; every later command raised `NNTPSyncError`.
- An unexpected multi-line success code left its reply on the connection, so
  the next command read stale data; it is now read and dropped first.
- `close()` and `quit()` can be called more than once; a `with` block closes the
  socket even if QUIT fails, and doesn't replace the block's own exception.
- Sockets leaked when the greeting, TLS or MODE READER failed during setup.
- After STARTTLS, plaintext buffered after the 382 reply was read as if it had
  come over TLS.
- AUTHINFO: no endless recursion when the server keeps answering 480, no bare
  `AUTHINFO USER` without a username, 483 is passed through.
- `post()` returns the Message-ID also for INN's `240 Article received <id>`.
- XHDR values kept their CRLF; the Message-ID form of XHDR failed.
- Overview fields marked `:full` kept their `Xref: ` label.
- gzip-compressed replies repeated or dropped data around the terminator and
  left the gzip trailer on the connection.
- `NNTPProtocolError` carried bytes; an empty status line raised `IndexError`.
- Text after a yEnc `=yend` line was decoded as data.

### Development

- Offline tests against a scripted NNTP server (`tests/scripted.py`); about 450
  tests in all.
- CI on GitHub: ruff, ruff format, mypy --strict, and the tests on Python
  3.10-3.14 against INN from Ubuntu's `inn2` package
  (`tests/integration/inn2/setup.sh`).
- Dependencies in `poetry.lock` refreshed; `pre-commit` is no longer a Poetry
  dev dependency.
- New changes add a one-line fragment in `changes/` (see `changes/README.md`).

## 2.0.1 (2024-09-29) and earlier

See the upstream project, https://github.com/greenbender/pynntp.
