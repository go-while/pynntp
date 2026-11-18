# Council R2b — 1: fix/yenc-unclosed-block

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `2cf7f35ad83a4bc7ed44ce7e6e9444e38024081f`.
Scope: the whole PR, including its regression and surrounding decoder.
Earlier review reports were not consulted for this review.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

- `_decode_yenc()` decodes pending first-block data before recognizing the next
  control line. The new open-block check at `nntp/nntp.py:1455–1458` saves the
  missing-trailer error before replacing the decoder and counters.
- Later valid trailers cannot clear that saved error. The response is consumed
  before raising, and both blocks' decoded bytes remain available in `.data`.
- A properly closed block followed by another block is unchanged. The added
  test checks missing-trailer detection, retained data and the following DATE
  at the existing chunk fixture sizes.

## Notes — not findings

The already-filed stray-trailer issue #159/PR170 is separate and not counted.
No style or speculative hardening requests.

## Verification and limits

Confirmed by source reading. I did not run tests, benchmarks, linters, a real
provider or a combined-branch integration check. The lead's stated host checks
are not claimed as my runs. No tree edits, installs, commits or GitHub writes;
G1 observed. No host job was started.

1 fix/yenc-unclosed-block: 10, 0 findings (0H/0M/0L); below 9.5 because: -
