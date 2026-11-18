## Findings
Nothing found.

## Notes
- **Callers:** `nntp/nntp.py:1588` passes `allow_msgid` by name. All calls in `tests/test_utils.py:282–314` use either one argument or `allow_msgid=False`. Repository-wide search found no positional second argument or documentation example that breaks.
- **Public API:** Treat this as public: `CHANGELOG.md:7–10` explicitly advertises `utils.parse_number_value()`, despite its absence from top-level exports. Nevertheless, upstream 3.3.0 accepts only `line`, so making the newly introduced option keyword-only preserves existing supported calls. Only callers adopting the intermediate, unreleased positional option would break.
- **Behaviour:** `nntp/utils.py:164` retains the same default and implementation; the updated caller supplies the same value. No silent parsing or error-handling change.
- Reviewed by reading only; no commands or tests run. The reported test-host results are lead-provided, not independently verified.

#174 e339eda: 9.5, 0 findings (H/M/L): -
