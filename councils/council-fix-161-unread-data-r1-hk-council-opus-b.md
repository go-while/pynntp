# Council r1: fix/161-unread-data (976d46e), reviewer hk-council-opus-b

Diff: `git diff upstream/main...origin/fix/161-unread-data` (base 2bfca17, 3 commits). Read only; not run on a test host. Reviewed fresh; the earlier Opus review was not read.

**Score: 9/10**

No findings. `_check_nothing_unread()` runs inside `_sync()` before every `_send()` of a command (`_command`, nntp/nntp.py:727) and before the article body in `_transfer` (:1904). Those are the only two places that write to the socket. A hit raises `NNTPProtocolError`, sends nothing and leaves `_broken` set, so every later command gets `NNTPSyncError` until `reconnect()`. That matches the existing STARTTLS-382 check and the suggestion in #161.

| Sev | File:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| (none) | | | | | |

Checked for false positives, which are the main risk of this change:
- **Only the buffer is checked, not the socket.** Data from a well-behaved server (it answers, then waits) can never be in the buffer when the next command is sent. An idle-timeout "400" sent later stays in the socket and is read as the next reply, as before.
- **Nothing that worked before now fails.** Any data left in the buffer was already read as the next status line before this PR. That either raised (`"."`, an empty line or text gives `NNTPProtocolError`; the wrong code gives `NNTPReplyError`) or silently shifted every later reply. The PR only turns the silent shift into an error, before the command is sent. This includes `__exit__`/QUIT, which raised in the same cases before.
- **COMPRESS:** `_inflate_more` is drained with `_decompress(b"")` before the check, so output held back by the 64 KiB limit counts as data, while a sync flush that inflates to nothing does not. A flush marker arriving in a later recv is still in the socket and does no harm. Errors from `_decompress` close the connection, as before.
- **The data `compress()` and `_info_gzip()` put back** (:1028, :528) is by definition data sent beyond the reply, so refusing it is right. The gzip TERMINATOR path drains the stream to EOF before putting anything back.
- **Login retry:** `login()` and the retried command each go through `_command`, so each one is checked.

Tests: the new `FakeSocket` stops each recv at the end of a reply (`_reply_ends`), and `Packets` forces boundaries where a test needs them. That is needed, because with chunk 4096 the old fake fed several replies in one recv, which is exactly what the fix now refuses. The branches that depend on data arriving together (compress() pending data, corrupt data with the 206, data after STARTTLS 382) moved to explicit `Packets` tests, so no coverage is lost. `list_of_inflate_size()` gives exactly `_INFLATE_SIZE` octets (65 lines of 1000 plus 1 of 523) and reaches the `_inflate_more` branch as intended.

Not scored down, but worth knowing: the first error is `NNTPProtocolError`, not `NNTPSyncError`, so a caller whose only recovery is `except NNTPSyncError: reconnect()` sees one exception it does not catch. The docstrings say so, and it matches the existing STARTTLS behaviour.
