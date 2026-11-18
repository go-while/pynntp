## Finding

- **`tests/integration/inn2/test_inn2.py:571` — Low — confirmed by reading; new for the documented configurable-server use.** With a server where the configured credentials are `user` / `secret` and those credentials are accepted, this test’s supposedly rejected login can succeed, so the test fails at `pytest.raises`. That is a wrong failure verdict for a valid credential configuration.

## Notes

- No other findings.
- I did not run tests or connect to a server. The environment integrity check could not be run because shell access was denied.

**Score: 9.0/10.** The credential-dependent false failure keeps this below the 9.5 target.

#167: 9.0, 1 findings (H0/M0/L1): configured credentials can make rejected-login test succeed
