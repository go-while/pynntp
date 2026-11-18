**All four round-1 findings are fixed. No new findings confirmed in the delta. Score: 9.5/10.**

| Round-1 finding | Status | Confirmation at head |
|---|---|---|
| Pre-login capability gates | Fixed | `tests/integration/inn2/test_inn2.py:146–151` logs in when credentials and `AUTHINFO USER` are available, then reads capabilities again. Retains pre-login STARTTLS. |
| Wrong credentials retained after refused login | Fixed | `tests/integration/inn2/test_inn2.py:611` restores configured credentials before DATE, enabling automatic authentication on 480. |
| Remote INN requires stock groups | Fixed | `tests/integration/inn2/test_inn2.py:86,110–115` checks configured groups through LIST ACTIVE whenever HOST or GROUPS is set. |
| Unbracketed IPv6 URL | Fixed | `tests/integration/inn2/test_inn2.py:91,643,651` brackets IPv6 literals in both URL tests. |

**New findings:** Nothing found.

**Notes**
- Confirmed by reading only; no commands or tests run. Reported test results are the lead’s, not independently verified.
- The no-variable default retains its stock-group assertions.
- The read-only restriction prevented the required `the rules` checksum/ownership command checks.

#167 r2: 9.5, 0 findings (H/M/L): -
