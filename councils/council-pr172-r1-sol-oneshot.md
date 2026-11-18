**No findings. Score: 9.5/10 — ready to merge.**

Confirmed by reading: `nntp/utils.py:204–218` removes line endings before unfolding, preserves whitespace between value pieces, and trims only the completed value. Joining once also removes quadratic continuation concatenation.

**Tests, assessed by reading:**
- The whitespace regression cases and HEAD regression would fail on the base and pass on the head. Some unchanged-behavior parameter cases pass on both.
- The large-continuation test produces the correct value on both versions; its timing assertion is machine-dependent, so base failure is not guaranteed.

**Notes, not findings:** `tests/test_utils.py:146–152` uses a wall-clock threshold that could be flaky on heavily loaded CI.

**Scope:** One concern: correct, efficient folded-header parsing.

**Not checked:** No commands or tests run. Rule-file hashes/ownership could not be verified within the read-only tool restriction. No broader library audit or live-server checks.

#172: 9.5, 0 findings (H/M/L): -
