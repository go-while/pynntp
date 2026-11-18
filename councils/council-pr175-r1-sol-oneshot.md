The new validation rejects all three reported malformed names while preserving metadata and trailing whitespace behavior. I cannot verify `/etc/agents` hashes or ownership with the permitted read-only tools; no execution or host work will be attempted.
## Review: no findings

**Score: 10/10 — ready to merge.**

The validation at `nntp/utils.py:156–157` rejects empty, whitespace-padded and non-ASCII field names after metadata normalization. Valid header names, `:bytes`, case-insensitive `full`, and existing trailing-whitespace tolerance remain supported. Invalid formats raise `NNTPDataError` rather than entering the overview cache.

### Tests, assessed by reading
- The six new rejection cases would **fail on base and pass on head**.
- The three added trailing-whitespace acceptance cases would **pass on both**.
- No tests or programs were run.

**One concern:** yes—overview field-name validation and its regression coverage.

### Notes, not findings
- Parser failure uses the existing fail-closed behavior: the unread response marks the connection out of sync, requiring reconnection. This is deliberate error handling, not silent protocol desynchronization.
- The new command tests do not explicitly assert cache behavior or reconnection.

**Not checked:** runtime behavior, the full suite, live-server interoperability, or unrelated defects. Rule-file hashes and ownership could not be verified with the permitted read-only tools.

#175: 10, 0 findings (H/M/L): -
