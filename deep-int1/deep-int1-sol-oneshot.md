I’ll read the full library and the changed tests/CI, checking protocol state and data integrity in particular. This will be a read-only review; I won’t run project code on the workstation.
The full library read is complete. I found a posting path that can alter dot-prefixed header names, and I’m checking two compressed-response cases that may silently lose rows. I’m also checking whether reconnect can retain an outdated overview format.
## Outcome

**5 findings: 0 High, 4 Med, 1 Low. Score: 7/10.**

All five library defects are **pre-existing in 3.3.0**. The new fault suite also treats one problematic behavior as success. All findings below are **confirmed by reading**, not execution.

### 1. Med — Posted header names are not dot-stuffed

**Location:** `nntp/nntp.py:2135–2138`

**Trigger:** Post an otherwise valid article containing the extension header `"..X-Test": "value"`.

**What happens:** The library sends `..X-Test: value`, rather than the required `...X-Test: value`. A compliant receiving server removes one leading dot, changing the stored header name to `.X-Test`. POST and IHAVE share this path.

**Evidence:**
```python
article.write(hdrs.encode(self.encoding, self.errors))
for line in lines:
    if line.startswith(b"."):
        line = b"." + line
```
Headers bypass the dot-stuffing applied to body lines. `nntp/utils.py:260` accepts dot-prefixed field names.

- **Origin:** Pre-existing.
- **Harm:** Data corruption.
- **Who:** Caller supplying valid headers.
- **Crash:** None; the affected article is altered.
- **Exploit:** Data integrity; code-confirmed, not runtime-demonstrated.
- **Conditions:** Default configuration; POST or IHAVE.
- **Verdict:** Fix soon. Dot-stuff the entire article, including headers.

### 2. Med — Reconnect retains the previous connection’s overview format

**Location:** `nntp/nntp.py:1841–1844`, `nntp/nntp.py:1866–1886`

**Trigger:** Fetch overview data, reconnect after the server’s overview layout changes, then fetch overview data again. This can happen after server reconfiguration or reconnection to another backend.

**What happens:** `_overview_fields` remains cached across reconnect. If two optional columns exchange positions, their values are silently returned under the old names. No malformed server response is required.

**Evidence:**
```python
@cached_property
def _overview_fields(self):
    ...
    return tuple(self.list_overview_fmt())
```
The parser subsequently uses:
```python
names = self.overview_fmt
...
yield articleno, HeaderDict._from_fields(keys, names, values)
```
Neither `_connect()` nor `reconnect()` invalidates that cached property.

- **Origin:** Pre-existing.
- **Harm:** Data corruption through incorrect field attribution.
- **Who:** Server through a legitimate layout change; caller reconnects.
- **Crash:** None; subsequent overview results are affected.
- **Exploit:** Data integrity; code-confirmed, not runtime-demonstrated.
- **Conditions:** Default configuration; format fetched before reconnect and changed afterward.
- **Verdict:** Fix soon. Invalidate connection-derived overview metadata on reconnect.

### 3. Med — XZ responses silently ignore bytes after the DEFLATE stream

**Location:** `nntp/nntp.py:647–658`; shared decompression helper at `nntp/nntp.py:229`

**Trigger:** An XZVER/XZHDR response contains one yEnc block encoding `finished_DEFLATE(rows_A) + finished_DEFLATE(rows_B)`, with a correct yEnc size and CRC covering both.

**What happens:** Only `rows_A` is returned. The second stream lands in `inflate.unused_data`, which this path never checks. Trailer validation succeeds because it covers the encoded input, not whether all that input was decompressed.

Continued trailing input can also grow zlib’s retained `unused_data`, defeating bounded-memory expectations for these streaming methods.

**Evidence:**
```python
return inflate.decompress(inflate.unconsumed_tail + data, _INFLATE_SIZE)
```
XZ validation checks the yEnc trailer and:
```python
if not inflate.eof:
    raise NNTPDataError(...)
```
It never rejects nonempty `inflate.unused_data`.

The **new** `tests/faults/scenarios.py:1616–1622` explicitly expects success for trailing compressed-stream junk, protecting this acceptance behavior rather than detecting it.

- **Origin:** Library defect pre-existing; permissive fault-test expectation new.
- **Harm:** Silent data loss; potentially DoS through retained trailing input.
- **Who:** Buggy or hostile server.
- **Crash:** None for the finite two-stream trigger; sufficiently large tails can exhaust the client process’s memory.
- **Exploit:** Data integrity/DoS; code-confirmed, not runtime-demonstrated.
- **Conditions:** XZVER/XZHDR; trailing bytes inside the checked yEnc block.
- **Verdict:** Fix soon. Reject unexpected bytes after the DEFLATE stream.

### 4. Med — Mixed LF/CRLF XZ rows are silently merged

**Location:** `nntp/nntp.py:609`, `nntp/nntp.py:661–664`

**Trigger:** A finished, correctly checksummed XZHDR payload decompresses to:
```text
1 one\n2 two\r\n
```

**What happens:** It returns:
```python
[(1, "one\n2 two")]
```
instead of reporting malformed framing. The second row disappears into the first value.

**Evidence:**
```python
yield from self._lines(buf)
```
`_lines()` splits only at CRLF and does not reject embedded LF. The newly added check:
```python
if last := buf.read():
    if b"\n" in last:
        raise NNTPDataError(...)
```
examines only the leftover fragment. Here the entire payload was already emitted as one CRLF-terminated line, leaving nothing to check.

- **Origin:** Pre-existing; the new bare-LF check leaves this case unfixed.
- **Harm:** Data loss and corrupted header values.
- **Who:** Buggy or hostile server.
- **Crash:** None; the response succeeds with incorrect results.
- **Exploit:** Data integrity; code-confirmed, not runtime-demonstrated.
- **Conditions:** XZVER/XZHDR with mixed line endings; no packet-timing requirement.
- **Verdict:** Fix soon. Validate each decompressed line before yielding it.

### 5. Low — Oversized decimal fields escape as raw `ValueError`

**Location:** `nntp/yenc.py:93`; also `nntp/nntp.py:1547`

**Trigger:** With CPython’s default integer-conversion limit, send either:

- A yEnc trailer whose `size=` contains 4,301 decimal digits.
- A STAT/NEXT/LAST `223` reply with a 4,301-digit article number and a valid message-id.

Both fit below the default response-line limit.

**What happens:** `int()` raises `ValueError`, escaping the documented NNTP exception hierarchy. The yEnc case also bypasses `NNTPYEncError.data`.

**Evidence:**
```python
if int(expected_size) != size:
```
and:
```python
return int(parts[0]), parts[1]
```
Neither conversion is inside an exception-normalizing handler.

- **Origin:** Pre-existing.
- **Harm:** Crash of a client task whose error handling catches `NNTPError`/`OSError`.
- **Who:** Server.
- **Crash:** Calling task/process if uncaught; impact on other users depends on application isolation. Server unaffected.
- **Exploit:** DoS only; theoretical exploitation, code-confirmed trigger.
- **Conditions:** Default CPython integer limit and default line limit.
- **Verdict:** Issue list only; normalize conversion failures to the appropriate NNTP data exception.

## Notes

- No additional finding in `fifo.py`, `headerdict.py`, `types.py`, or `__init__.py`.
- No new CI secret-exposure or privilege-escalation finding established.
- `tests/faults/README.md` still lists several resolved scenarios as known failures.
- Apart from finding 3’s expectation, no additional actionable test-verdict defect established.
- The requested known issues were excluded.

## Coverage and limits

Read every library file, the supplied test/CI diff, and the checked-out tests and workflows. Confirmed the checkout is `e07f041`.

**Not checked by execution:** tests, reproducers, timing, memory measurements, or interoperability with real servers. External action implementations, dependencies, and the Go fake-server implementation were not audited.

The score is held below 10 by silent article/header alteration, stale reconnect metadata, compressed-response data loss, and incomplete exception normalization.

deep-int1: 7, 5 findings (0H/4M/1L): header dot-stuffing; stale overview cache; ignored XZ tail; merged XZ rows; raw integer ValueError
