The new tail handling runs only after trailer validation and DEFLATE EOF, so it does not return an unvalidated final row. I’m checking the row parsers and line-length checks for effects of accepting a row without CRLF. This is a read-only review; I cannot perform the required rules-file hash/ownership verification here.
**No findings. Score: 9.5/10.** The change fixes the silent last-row loss without bypassing trailer validation, DEFLATE EOF checking, or existing line-length limits. Both row parsers support the unterminated final row.

- **Tests, by reading:** Unterminated-row and bare-LF cases would fail on base `2bfca17` and pass on head `8ac5794`. Terminated-row, empty-stream, and bad-trailer cases should pass on both.
- **One concern:** Yes—handling the final buffered XZVER/XZHDR row safely.
- **Notes, not findings:** Optional coverage could verify reconnect behavior after the new bare-LF error and an unterminated row split across multiple yEnc lines.
- **Not checked:** Runtime tests, builds, live-server interoperability, unrelated defects, or external issue history. Rules-file hash/ownership verification was unavailable under the read-only restriction.

No identified merge blocker.

#171: 9.5, 0 findings (H/M/L): -
