# Round 0 review: PR #169 (fix/156-post-msgid, head eaa79ed)

Reviewer: hk-r0-haiku-a (Haiku 5.5, round 0, read-only). Base: upstream/main 2bfca17.
Scope: #156, post() took the first `<...>` anywhere in the 240 reply as the Message-ID.
Method: read nntp/nntp.py post() (head :1779-1819), _transfer, _prepare_article, _MESSAGE_ID_RE (:66), and
the test diff. Issue #156 text read. No code run here, no host run.

## Findings

### 1. Low: a Message-ID that is not in the first reply position is no longer returned (silent, type changes to True)

- File: nntp/nntp.py:1813-1819 (head). `parts = message.split()`; the id is accepted only as parts[0], or
  parts[0] after an "Article received" prefix (casefold).
- Trigger: a server (any, hostile or not) whose 240 reply carries the id after other text, e.g.
  `240 Article received ok <new@id>` or `240 Article posted ok, id <new@id>`, or a trailing dot
  `240 Article received <new@id>.`. Under the base code these returned `<new@id>`; under the head they return
  `True`.
- What goes wrong: post() still succeeds, but the caller that reads the id (`isinstance(result, str)`, or uses
  the returned id to track the article) gets `True` and loses the id silently. The return type is
  `str | bool`, so no error is raised.
- Confirmed by: reading only (the diff's `return True` branch). Not confirmed that any real server sends such a
  reply; the repo's tests and the issue #156 cite only the first-position and "Article received <id>" shapes
  (see tests/test_posting.py, base and head). The docstring of the head says the id is returned "if it is the
  first reply token or follows INN's 'Article received' prefix", so the narrowing is documented. The harm
  depends on whether a server in use sends the id later, which this review cannot show.
- New in the change (the base returned any id). Severity Low because it needs a server format we have no
  evidence for; the issue itself is rated low.

## Checked by reading (no finding)

- The reported case of #156 (`240 posted ok; report abuse to <abuse@example.net>` returns True now) is fixed.
- Regex `<[!-=?-~]{1,248}>` fullmatch on a single whitespace-free token: a token cannot contain a space, so
  `<bad id>` cannot match (test case expects True). Covered.
- Empty reply (`240` alone, or an empty message): `parts` is empty, returns True. Covered.
- Casefold of "Article received" and the `parts[2:]` slice: correct for "ARTICLE RECEIVED <id>".
- `_transfer` (:1875-1904): `message` is the 240 status text, returned after `code == done`. The new code
  only changes what `post()` does with it.
- Tests (base vs head): the new parametrised cases such as `240 posted ok; report abuse to <abuse@example.net>`
  return a `<...>` on base and True on head, so these fail on base and pass on head by reading. The added
  `client.date().year == 2024` assertion checks that the connection stays in sync after the 240 line.
- Docstring: the Returns text matches the code.

## Notes (not findings)

- Test comments name servers (OUS, Diablo, NewsCache, go-pugleaf) as sources of the reply shapes. Those
  shapes are not verified here; they are comments only.
- `(b"240 <bad<id> posted", "<bad<id>")`: RFC 3977 allows "<" in an id per the test comment. Not checked against
  RFC 5536 (which requires "@"); a style point, the head follows the existing regex.
- Single concern (how post() reads the id from the 240 reply). One commit.

## Did not check

- The real replies of INN, Diablo, NewsCache, OUS, go-pugleaf (no network, no host run).
- Whether any caller in the repo or in greenbender's users depends on the id being returned from non-first
  positions.

## Score

8.5 / 10. Ready apart from the question in finding 1: if a server in use puts the id later, the head drops it
silently. A short note in the docstring, or keeping the fallback search for ids that are not first, would close
it.
