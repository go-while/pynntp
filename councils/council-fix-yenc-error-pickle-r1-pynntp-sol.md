# Council R1 — 4: fix/yenc-error-pickle

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `a0e15a724d7bdd763302b58e025e1b20019f67e5`.

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| — | — | — | No findings in the change. | — | — |

Inspected NNTPYEncError.__init__ and the new __reduce__ return value. Rebuilding
the exception now supplies both required constructor arguments, preserving the
single-message .args representation and decoded bytes in .data. The third
element retains instance state, including exception notes and additional
attributes; it also supports copy/deepcopy using the same reconstruction.
No decoding or exception-raising path changes. The submitted tests exercise
pickle, shallow/deep copying, concrete error type, notes, args and data.

Verification: code reading only, not a claim of an executed pickle test.
Optional host checks not run; no local project execution, tree edits, commits,
installs or GitHub writes. G1 observed.

4 fix/yenc-error-pickle: 10, 0 findings (0H/0M/0L)
