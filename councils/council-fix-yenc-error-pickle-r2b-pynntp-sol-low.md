# Council R2b — 4: fix/yenc-error-pickle

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `a0e15a724d7bdd763302b58e025e1b20019f67e5`.
Scope: the complete reduction change and new exception-copy tests.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

The reduction at `nntp/nntp.py:249–255` reconstructs NNTPYEncError with both
required constructor arguments: its message and decoded bytes. Returning the
instance dictionary as state preserves extra attributes and notes. This agrees
with the constructor's single-message `.args` and separate `.data` field.
Shallow/deep copying can use the same reconstruction instead of invoking a
two-argument constructor with only its message.

The added tests check type, string, args, dictionary state, notes and decoded
data for pickle and copy operations. No changes to yEnc decoding, error
selection or connection state are part of this PR.

## Notes — not findings

No actionable non-finding notes. Hypothetical custom exception subclasses
with unrelated constructor protocols are not asserted as a defect here.

## Verification and limits

Source and test-reading review, not an executed pickle/copy or multiprocessing
test. I did not rerun the lead's checks. No local project execution, tree edits,
commits, installs, host jobs or GitHub writes. G1 observed.

4 fix/yenc-error-pickle: 10, 0 findings (0H/0M/0L); below 9.5 because: -
