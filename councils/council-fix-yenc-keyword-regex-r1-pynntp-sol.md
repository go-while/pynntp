# Council R1 — 6: fix/yenc-keyword-regex

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `54751e29aae85e4f6127fdd3941abbef99221a04`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

The negative one-byte word lookbehind allows a candidate key only at the
beginning of a word run. A long word with no equals sign can therefore no
longer cause a full suffix search from each interior position. It leaves the
existing greedy key/value captures unchanged at real candidate positions.
The preceding filename split and byte-to-ASCII handling are unchanged.

Inspected table cases for punctuation-separated keys, underscores/digits,
empty values and equals signs inside values, plus the trailer/size/CRC callers.
No changed parsing result for a normal key=value line was identified. No timing
or resource-exhaustion experiment was run locally.

Verification: regex/control-flow review only; optional test-host execution
not used. No tree edits, commits, installs or GitHub writes. G1 observed.

6 fix/yenc-keyword-regex: 10, 0 findings (0H/0M/0L)
