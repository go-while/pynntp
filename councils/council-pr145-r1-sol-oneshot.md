## Finding

1. **Med — Known failures suppress server-side mismatch failures**  
   **`tests/faults/scenarios.py:2716–2721`** — New in this change; confirmed by reading.

   Server mismatches and `server_check` are examined only when the client-side reason is empty. A known scenario already has a nonempty reason, so unexpected client commands recorded alongside the expected bug are ignored. `test_faults.py` consequently reports XFAIL rather than failing for the additional regression.

   For example, `malformed/group-negative-numbers` still qualifies for XFAIL whenever its client result produces the expected failure fragment, even if the server summary also reports unexpected client lines. This contradicts the documented exclusion of server-side problems from known failures.

   **Fix:** evaluate server-side checks independently of the client verdict and append their failures, as already done for missing summaries and nonzero server exits.

## Notes

- All eight `known=` cases correspond to the bug mechanisms present in the checked-out client. Their markers default to strict, so a passing scenario produces a failing XPASS.
- The negative-GROUP marker’s fragment matches **any returned result**, rather than specifically the existing negative tuple; tightening it would distinguish changed wrong outcomes.
- The workflow uses SHA-pinned actions, a versioned server dependency, read-only permissions, and no explicit secrets or PR trigger.

## Scope and score

Reviewed the supplied change, supporting client implementations, and `pr-text.md`. No tests were run; the lead’s reported results were not independently reproduced. I did not verify live GitHub issue/PR status, action SHA provenance, or the external fake-server implementation.

**Score: 9/10.** The server-verdict suppression above keeps this below 9.5.

#145: 9, 1 findings (0H/1M/0L): Known failures suppress server mismatches
