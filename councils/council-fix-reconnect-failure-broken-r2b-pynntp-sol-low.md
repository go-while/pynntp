# Council R2b — 3: fix/reconnect-failure-broken

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `0ae1bd3c21a0eb28495e142a20571e43abc660d5`.
Scope: the whole PR and connection/reconnection failure paths.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

`reconnect()` first calls close(), marking the old socket broken. Moving
`_broken=False` after create_connection at `nntp/nntp.py:318–321` means a failed
connect leaves that broken state intact. A later successful connection resets
it normally. Greeting/TLS failures still close the newly created socket through
the existing exception handler; reader-mode failure cleanup is unchanged.

The new regression's failed connection does not consume the next fake socket:
it checks command refusal after failure, then successful reconnect and DATE.
Initial construction failure still returns no client, so no normal caller
receives an object with an uninitialized `_broken` field.

## Notes — not findings

The known stale-iterator/reconnect issue #162 is separate, not a new result
of delaying this state reset. No unrelated retry policy is requested.

## Verification and limits

Confirmed by reading code and tests; no runtime refusal, TLS handshake,
DNS fault or test suite was run by me. The lead's stated host checks were
not independently rerun. No source edits, commits, installs, host jobs or
GitHub writes. G1 observed.

3 fix/reconnect-failure-broken: 10, 0 findings (0H/0M/0L); below 9.5 because: -
