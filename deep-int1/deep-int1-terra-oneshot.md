I’ll review the checked-out source and the supplied diff by reading; I won’t run project code on the workstation.
## Findings

### Medium — yEnc header size is not checked, allowing silent truncation

**Location:** `nntp/nntp.py:1616–1634`; `nntp/yenc.py:89–94`  
**Origin:** Pre-existing in 3.3.0. **Confirmed by reading.**

For a non-multipart body containing `=ybegin line=128 size=1 name=x`, then `=yend size=0`, followed by an encoded data line and no further trailer, `body()` returns `b""` successfully. The decoder closes the block at `=yend`, drops the subsequent line as outside the block, and checks only the trailer’s size against the decoded length. It never compares that length with the `=ybegin` size.

- **Harm:** Silent data loss or corruption.
- **Trigger:** A server delivering a malformed or corrupted article; this can also originate in posted content.
- **Crash:** None required.
- **Exploit:** Data integrity; demonstrated by the code path, not by a run.
- **Conditions:** Default yEnc autodetection or `decode=True`; a non-multipart block with a self-consistent premature trailer.
- **Verdict:** Fix soon.

### Medium — cached overview format survives reconnect and authentication changes

**Location:** `nntp/nntp.py:408–424`, `1841–1849`, `1865–1886`  
**Origin:** Pre-existing in 3.3.0. **Confirmed by reading.**

`_overview_fields` is a `cached_property`, while `reconnect()` replaces the connection without clearing it. If the reconnected endpoint advertises a different `LIST OVERVIEW.FMT`—for example, after a server configuration change or a connection to a different backend—the next overview is interpreted using the old field order. The same risk exists if authentication changes the format after it was cached. `_xover()` constructs field names from that cache and pairs them with the newly received values.

- **Harm:** Silent data corruption: overview values are attributed to the wrong headers.
- **Trigger:** Server/backend configuration or session changes.
- **Crash:** None required.
- **Exploit:** Data integrity; theoretical from the code path.
- **Conditions:** The client has already fetched the overview format and the server’s format subsequently changes.
- **Verdict:** Fix soon; invalidate the cache when session state can change.

### Low — HEAD now buffers even data after the header-ending blank line

**Location:** `nntp/nntp.py:1722–1726`  
**Origin:** New in the diff. **Confirmed by reading.**

A server can answer `HEAD` with a blank line followed by an arbitrarily large number of short lines before the dot terminator. The new `lines = list(self._info(code, message))` retains the entire response, although `parse_headers()` subsequently ignores everything after the blank line. The per-line limit does not bound the number of lines. Previously parsing stopped at the blank line rather than collecting the remainder.

- **Harm:** DoS through unbounded memory consumption.
- **Trigger:** The selected server.
- **Crash:** Potentially the process using the client; all users served by that process may be affected.
- **Exploit:** DoS; theoretical from the code path.
- **Conditions:** A malformed or hostile HEAD response; default configuration.
- **Verdict:** Fix soon. Parse incrementally and drain ignored lines without retaining them.

### Low — oversized yEnc trailer size escapes as `ValueError`

**Location:** `nntp/yenc.py:89–94`; `nntp/nntp.py:1621–1624`  
**Origin:** Pre-existing in 3.3.0. **Confirmed by reading.**

A `=yend size=` value containing, for example, 5,000 ASCII digits fits under the default line limit and passes `_DIGITS_RE`, but on Python’s default integer-string conversion limit `int(expected_size)` raises `ValueError`. It escapes `body()` rather than becoming the documented `NNTPYEncError` or another `NNTPError`.

- **Harm:** Wrong exception type; potentially an uncaught application error.
- **Trigger:** The selected server or malformed article content.
- **Crash:** An application process that catches only documented NNTP errors may terminate; impact depends on the application.
- **Exploit:** DoS; theoretical from the code path.
- **Conditions:** Python’s integer conversion limit is enabled and the yEnc trailer contains an oversized decimal size.
- **Verdict:** Issue list only.

### Low — integration capability matching can skip supported tests

**Location:** `tests/integration/inn2/test_inn2.py:124–129`, `159–170`  
**Origin:** New in the diff. **Confirmed by reading.**

`offers_login()` and `require()` compare capability tokens with uppercase strings without normalizing the server’s tokens. A server advertising equivalent lowercase or mixed-case capability names or keywords can therefore be treated as not offering `AUTHINFO USER`, `STARTTLS`, or another feature. In the `require()` case, the associated integration test skips rather than checking the client.

- **Harm:** Test-only: a skipped gate and reduced integration coverage.
- **Trigger:** The integration-test server’s capability spelling.
- **Crash:** None.
- **Exploit:** No security exploit shown.
- **Conditions:** Configurable integration tests against a server using different case in capability tokens.
- **Verdict:** Fix soon; compare capability tokens case-insensitively.

## Notes and coverage

I read every file in `nntp/` and inspected the supplied diff, including the changed integration and fault-test machinery and the principal CI workflow. I did **not** independently read every unchanged test or every CI workflow in full, run tests or reproducers, verify the Git head with Git, or exercise real servers. All findings above are therefore reading-based; none is a claim that a test passed. I did not report the listed known issues.

**Score: 6/10.** Silent yEnc truncation and stale overview-format interpretation keep this head from a 10; the new HEAD buffering path and test-gating issue also warrant attention.

deep-int1: 6, 5 findings (H/M/L: 0/2/3): yEnc truncation, stale overview format, HEAD buffering, oversized yEnc size exception, capability-case skips
