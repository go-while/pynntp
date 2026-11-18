# Council R2b — 6: fix/yenc-keyword-regex

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `54751e29aae85e4f6127fdd3941abbef99221a04`.
Scope: the whole regex change, parsing callers and submitted tests.
Earlier review reports were not consulted.

## Findings

None. No new defect meeting the Findings test identified.

## Code evidence

At `nntp/yenc.py:27–29`, the word lookbehind prevents retries inside the same
word run. A failed key candidate without equals is therefore scanned once,
not from every suffix. At a valid key start, the same greedy word/equal/value
pattern still applies; the value can be empty and consumes its non-whitespace
contents without a later failing suffix in the regex.

Filename exclusion before matching and trailer size/CRC interpretation are
unchanged. Table tests cover underscore/digit keys, punctuation boundaries,
empty values and embedded equals; the client-level test preserves decoding
and synchronization with long words on control lines.

## Notes — not findings

No style or performance-threshold suggestions are counted. The regex retains
the prior permissive keyword language; this PR is not a keyword-policy rewrite.

## Verification and limits

Reasoned from the regex and callers; I did not execute the timing assertion,
generate load, run a provider test or rerun the lead's checks. No local project
code, tree edits, commits, installs, host jobs or GitHub writes. G1 observed.

6 fix/yenc-keyword-regex: 10, 0 findings (0H/0M/0L); below 9.5 because: -
