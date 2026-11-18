# Council r2b: fix/ssl-context-plaintext

- **Head:** `9a3379d89fcb40c2214346765bcfa2b17d736d01`; base `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
- **Score:** 9.5/10. **Findings:** 0 (H/M/L: 0/0/0).
- **Review by reading:** `SSLMode(ssl_mode)` runs before the connection when `use_ssl` is true; both enum members and their lowercase string values normalize to the existing TLS branches and port defaults. Invalid modes now raise before socket creation. With `use_ssl=False`, previous plaintext and ignored-context behavior remains. URL schemes still select their own TLS mode and forward the supplied context.
- **Notes, not findings:** the changed default-port test for lowercase strings stops at the socket-creation boundary; it does not itself exercise a completed TLS handshake. Existing TLS URL tests inspect context use, but this review did not independently verify real TLS interoperability.
- **Prior context:** I previously reviewed the upstream session/TLS area; I do not recall an earlier finding about this particular invalid-`ssl_mode` change.
- **Not checked:** no tests, probes, real server connections, CI results or certificate verification runs; no branches or GitHub state were modified. This is a reading review, not a claim that tests passed.

9 fix/ssl-context-plaintext: 9.5, 0 findings (0/0/0); below 9.5 because: -
