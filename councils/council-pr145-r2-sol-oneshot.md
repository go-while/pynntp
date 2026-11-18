All three round-1 items are fixed, confirmed by reading:

1. **Server failures hidden by client failures — fixed.** `tests/faults/scenarios.py:2736–2744` evaluates mismatches and server checks independently and appends their reasons. `tests/faults/test_faults.py:50–51` makes these real failures even for known scenarios.
2. **Late-broken clean errors accepted — fixed.** `tests/faults/scenarios.py:2446–2449,2466–2469` rejects late-broken connections for `Clean` errors and `Err(state="any")`, unless explicitly permitted. Desync remains rejected earlier.
3. **Misleading POST comment — fixed.** `tests/faults/scenarios.py:1833–1835` correctly states that the server reads nothing after POST.

**New findings:** Nothing found in the delta.

**Notes**
- Reading-only review; no commands or tests run. Test results are the lead’s supplied results, not independently verified.
- The required rules checksum/ownership verification could not be performed under the no-execution restriction.

**Score: 9.5/10.** The open defects are resolved, with no new harmful verdict or lifecycle issue identified in the delta.

#145 r2: 9.5, 0 findings (H/M/L): -
