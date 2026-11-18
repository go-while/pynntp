I’ll review the parser changes and tests by reading only. I can’t verify `the rules` hashes or ownership under the no-execution restriction; I won’t run code or connect to hosts.
## Outcome

**8/10 — two new regressions prevent reaching 9.5:** silent truncation of whitespace-encoded data and rejection of complete blocks followed by signatures and duplicate trailers.

### Findings

1. **Med — Whitespace-encoded data can be silently lost**  
   **Location:** `nntp/nntp.py:1470` and `:1480`  
   **Trigger:** A poster or broken server supplies this BODY response, using default decoding:
   ```python
   b"222 1 <a@b>\r\n"
   b"=ybegin line=128 size=1 name=x\r\n"
   b"=yend size=0\r\n"
   b" \r\n"
   b"=yend size=1\r\n.\r\n"
   ```
   The space encodes byte `0xf6`; it is not an empty data line. However, `line.strip()` makes `dropped` remain false. The final trailer is ignored, and `body()` returns `b""` successfully. The base instead raises a size mismatch against the final trailer. CRC omission is supported.  
   **Confirmed by reading; new in this change.**

2. **Low — Signature followed by a duplicate trailer rejects intact data**  
   **Location:** `nntp/nntp.py:1480`  
   **Trigger:** A poster supplies:
   ```python
   b"222 1 <a@b>\r\n"
   b"=ybegin line=128 size=1 name=x\r\n"
   b"k\r\n=yend size=1\r\n"
   b"-- \r\nsignature\r\n"
   b"=yend size=1\r\n.\r\n"
   ```
   The complete block correctly decodes to `b"A"`. Signature text sets `dropped`, so the duplicate trailer produces a false `NNTPYEncError`, rejecting an otherwise successful download. The base accepts this exact input because both trailers match. The decoded bytes remain available through the exception.  
   **Confirmed by reading; new in this change.**

### Tests and scope

- **Base versus head, by reading:** The added stray-trailer success tests should fail on base and pass on head. Early-trailer and second-block tests also distinguish the implementations, sometimes through their expected error text. The bad-block-preservation test should pass on both. **Nothing was executed.**
- **One concern:** Yes—yEnc trailer handling after block closure, including XZVER/XZHDR.
- **Notes:** Neither finding is covered by the added tests.
- **Not checked:** Runtime behavior, CI, live servers, unrelated code, or the full external issue tracker/#145 beyond the supplied brief and checkout.

#170: 8/10, 2 findings (H/M/L: 0/1/1): whitespace-data truncation; duplicate trailer after signature rejected
