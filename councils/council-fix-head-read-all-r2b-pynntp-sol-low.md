# Council R2b — 8: fix/head-read-all

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `edbe1999829b0afd37df4ab65957875d83850046`.
Scope: the whole HEAD/ARTICLE change, reply/error helpers and submitted tests.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

HEAD at `nntp/nntp.py:1543–1549` finishes the raw response before parsing it.
An early blank or bad header cannot strand a live reply iterator; successful
drain clears reading state, and later parse/decode failures do not falsely
mark a fully consumed response out of sync.

ARTICLE at1505–1514 retains its single shared header/body iterator. Header
ValueError causes the remainder to be drained as raw lines before raising
NNTPDataError. It does not decode body data as headers. If draining itself
fails, the I/O error propagates and _response's finally preserves broken state,
instead of pretending the session is reusable. Valid headers still hand the
remaining iterator to the body decoder.

The tests include malformed/blank HEAD input, bad ARTICLE headers, following
DATE after successful drain, and disconnects both during HEAD and during
ARTICLE cleanup.

## Notes — not findings

Known reconnect/iterator and compression issues in #166 are not newly attributed
to this PR. No speculative aggregate-size policy is requested as a finding.

## Verification and limits

Confirmed by reading source and test cases, not by running them. No real server,
network failure simulation, resource test or combined-branch run was performed.
The lead's host checks were not independently rerun. No tree edits, commits,
installs, host jobs or GitHub writes. G1 observed.

8 fix/head-read-all: 10, 0 findings (0H/0M/0L); below 9.5 because: -
