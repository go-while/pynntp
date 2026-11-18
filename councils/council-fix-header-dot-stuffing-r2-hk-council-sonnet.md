# Council R2, PR 5 fix/header-dot-stuffing (reviewer hk-council-sonnet)

Read: `git show 71edde9` and nntp/nntp.py at that commit (post(), ihave(), _prepare_article); `git grep -i "body line"` over the tree at 71edde9.
Host run (120): tree of 71edde9, pytest without integration: 1073 passed; mypy: no issues; ruff check and format --check: clean.

## Open finding
- Low ("Body line" in the CR/NUL error although headers go through the same check): fixed. The message is now "Article line contains a CR outside a CRLF ending, or a NUL" (nntp.py _prepare_article), and the Raises text of post(), ihave() and _prepare_article says "a line of the article (header or body)". The remaining case-insensitive "body line" hits at 71edde9 are the _SEND_SIZE comment and the post() sentence "Header and body lines starting with '.' are dot-stuffed", both correct.

## New bugs in the delta
Nothing found. Only message text, docstrings and the two test regexes changed; the regexes match the new text. The check itself (order of dot-stuffing, CRLF strip, CR/NUL test) is untouched. Code that matched on the old "Body line" text would break, but the message is not API and the tests were the only users in the tree.

Score: 9/10. 0 findings (0/0/0).
