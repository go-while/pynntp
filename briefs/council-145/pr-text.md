Adds `tests/faults`: scenarios that run pynntp over real TCP against the fake server of [nntp-testkit](https://github.com/go-while/nntp-testkit) (my Go NNTP test kit, MIT-licensed, pinned to the v0.13.0 tag) while the server misbehaves. The unit tests' fake socket can't do some of this, for example drop a TLS session, stall a handshake or reset a connection. The tests are opt-in and need Go, so the default `uv run pytest` and `check.yml` don't change.

- **Server:** nntp-testkit's `nntp-fakeserver` program, installed with `go install github.com/go-while/nntp-testkit/cmd/nntp-fakeserver@v0.13.0`, so no Go code lives in this repo. It serves one scenario from a JSON file: either a byte-exact script (read a client line, write these bytes in these pieces, then close, reset, start TLS or start reading DEFLATE) or the fake server's Store or IHAVE peer with its faults (drip, delay, drop in a multi-line block, close after N commands, 480 overrides). When it finishes, it prints what the client sent.
- **`tests/faults/scenarios.py`:** the scenarios, plus the runner. Each client runs in a child process under a deadline and a memory limit. After the action it sends DATE. A scenario passes if the result is right, or if the error is an `NNTPError`/`OSError` and the connection is either still in sync or marked broken. It fails on a hang, a wrong result, any other exception, a stale reply, or a failed server-side check (e.g. AUTHINFO sent before TLS or after COMPRESS).
- **`tests/faults/test_faults.py` + `conftest.py`:** one parametrized test per scenario. It is only collected when `PYNNTP_FAULT_SERVER` names the `nntp-fakeserver` binary.
- **`.github/workflows/faults.yml`:** `workflow_dispatch` plus a weekly schedule, not on push or PRs. It sets up Go 1.26, installs `nntp-fakeserver` at the pinned tag (`NNTP_TESTKIT` in the workflow) and runs the tests on the same Python matrix as `check.yml`. Actions are pinned by SHA (`actions/setup-go` v7.0.0 is new here).
- **`CONTRIBUTING.md`:** a short section that points to `tests/faults/README.md`.

| Family | What the server does |
|---|---|
| split | replies one byte per write, every split point, CR/LF split, Store with drip and line delay |
| code | unexpected status codes, also with a multi-line block, on every command |
| leftover | extra data after a reply, in the same packet |
| drop | close/RST before, inside and after status lines and blocks |
| timeout | delayed replies, stalls mid-block, after POST, in the TLS handshake |
| tls | implicit TLS and STARTTLS: drops, data after 382, refusals without fallback, login inside TLS |
| compress | COMPRESS DEFLATE: split sync markers, Z_PARTIAL_FLUSH like INN, corruption, data after stream end, a long body |
| gzip | XFEATURE COMPRESS GZIP with and without TERMINATOR, split trailers |
| xzver | XZVER/XZHDR: finished and sync-flushed streams, CRC/size errors, dot-stuffed yEnc lines |
| yenc | multipart, CRC/size mismatches, text around blocks, escapes split across packets |
| post / ihave | 441/437/435/436, drops mid-article (4 MB), 480 then login |
| auth | 480 on each command in the middle of a logged-in session (exactly one new login must follow), 481/482/502, 381 without a password |
| malformed | bad greetings, status lines, overview rows, non-UTF-8, NUL |
| longline | a line at and over `max_line_length` (#148), also over COMPRESS |
| session | abandoned response iterators and reconnect() |

## How to run

```sh
go install github.com/go-while/nntp-testkit/cmd/nntp-fakeserver@v0.13.0
PYNNTP_FAULT_SERVER=$(go env GOPATH)/bin/nntp-fakeserver uv run pytest tests/faults -rxX
```

`-k gzip` and the like select a subset.

## Expected failures

These scenarios fail on the current `main` (3.3.0). Each is an `xfail` with a one-line reason that names the open bug. `xfail_strict` is on, so a fix that makes one pass shows up as XPASS and fails the run, and the fix then removes the marker. Whichever of this PR and the fix lands second removes the matching `known=` markers.

| Scenario(s) | Open bug |
|---|---|
| `leftover/second-status-same-packet`, `leftover/status-after-terminator-same-packet`, `leftover/extra-line-after-greeting` | Data the server sent after a reply, in the same read, is taken as the reply to the next command. Every later reply is then shifted by one (#161, fix in #187) |
| `session/resume-abandoned-iterator-after-reconnect` | A response iterator resumed after `reconnect()` reads the new connection's reply (#162, fix in #168) |
| `xzver/sync-flushed-not-finished` | XZVER rejects a complete DEFLATE stream that is sync-flushed, not finished (#154) |
| `xzver/last-row-without-crlf` | XZVER drops a last row that has no CRLF (#160, fix in #171) |
| `yenc/stray-yend-after-block` | A `=yend` line after a complete block raises `NNTPYEncError` (#159, fix in #170) |
| `malformed/group-negative-numbers` | `group()` accepts negative numbers in the 211 reply (#157, fix in #173) |

`gzip/terminator-inside-trailer-late` is not a known failure: it pins today's behaviour (#155, the reply waits for the end of the gzip stream after the terminator) and has to change if #155 is changed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
