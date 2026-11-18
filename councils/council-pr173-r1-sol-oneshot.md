## Review: 95dae73

**No findings. Score: 9.5/10 — ready to merge.**

The check at `nntp/nntp.py:1282–1285` restricts all three numeric fields to ASCII decimal digits before conversion. Negative numbers, explicit plus signs, underscores, and Unicode digits raise the existing `NNTPDataError`. The response is already consumed, so rejecting its fields does not leave unread reply data.

- **Tests, by reading:** All 12 added cases would fail on the base because `int()` accepts their inputs, and pass on the head. The subsequent `date()` assertion checks continued synchronization.
- **One concern:** Yes—validating GROUP reply numbers, with regression coverage.
- **Notes, not findings:** The new missing-field guard has no dedicated added test. Valid zero values and leading zeros remain accepted.
- **Not checked:** Runtime behavior, full-suite results, live-server interoperability, or unrelated commands. No commands were run; rule-file hashes and ownership could not be verified using the permitted read/grep/glob tools.

#173: 9.5, 0 findings (H/M/L): -
