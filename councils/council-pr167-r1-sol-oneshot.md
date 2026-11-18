## Findings

1. **Med — Capability gates use the unauthenticated feature set**  
   `tests/integration/inn2/test_inn2.py:124–126`  
   With `PYNNTP_HOST`, `PYNNTP_USER` and `PYNNTP_PASS` configured, a server can accept MODE READER and CAPABILITIES anonymously but advertise features such as POST, OVER or NEWNEWS only after authentication. Merely supplying credentials does not log in in this case. The cached capabilities therefore omit supported features, silently skipping their tests—including compressed POST—even though the configured account can use them.  
   Authenticate before caching account-dependent capabilities, while retaining appropriate pre-authentication STARTTLS discovery.  
   **Confirmed by reading** the helper and client authentication paths. **New** in the configurable-login path.

2. **Low — IPv6 server addresses produce invalid test URLs**  
   `tests/integration/inn2/test_inn2.py:619` and `:627`  
   With `PYNNTP_HOST=::1` (or another IPv6 literal), ordinary clients receive a valid socket hostname, but URL tests construct URLs such as `nntp://::1` and `nntp://::1:119?...`. These lack the required IPv6 brackets and fail URL parsing rather than testing the client against the server. Supplying brackets in `PYNNTP_HOST` instead breaks ordinary socket connections.  
   Bracket IPv6 literals when constructing URLs, not when connecting directly.  
   **Confirmed by reading** URL construction and `from_url()` parsing. **New**.

## Notes and limits

- I found no loss of the existing assertions or unintended skips on the default localhost-INN path.
- Reviewed the supplied diff, head files, adjacent PR text and relevant client implementation. No tests, builds or live-server checks were run; the lead’s reported results are not independent verification.
- The read-only reviewer restrictions prevented the required shell-based rules-integrity check. No execution depended on those rules.
- No additional style or hardening notes.

**Score: 8.5/10.** The unauthenticated capability cache silently reduces coverage for supported authenticated servers; IPv6 configuration also causes false failures. These two defects keep this head below 9.5.

#167: 8.5, 2 findings (H/M/L: 0/1/1): pre-auth capability skips; invalid IPv6 URLs
