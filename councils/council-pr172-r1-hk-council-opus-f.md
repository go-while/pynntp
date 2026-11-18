# Council r1: PR #172 (fix/163-header-unfold, head 6416b2c), reviewer hk-council-opus-f

Base upstream/main 2bfca17. Reviewed: net diff, `parse_headers` at the head, its callers (`article()` nntp.py:1505, which
shares one iterator for headers and body; `head()` :1536), and the new tests. By reading only; no host run.

Score: **9.5**

## Findings
None.

## Checks
| Check | Result |
|---|---|
| One concern | Yes, in effect. The whitespace fix needs a whole-value strip, and the list-of-pieces structure that does it also removes the pre-existing quadratic concatenation (no in-place `+=`, since the tuple held a second reference). A hostile server could trigger that with many continuation lines, so it's worth fixing here. |
| Fails on base, passes on head (by reading) | `test_parse_headers_fold_whitespace`: base strips each piece (`"one" + " two"` instead of `"one  two"`). `test_head_folded_whitespace`: same through HEAD. `test_parse_headers_many_continuation_lines`: see the note. |
| Edge cases | CRLF and LF endings, lines without endings, StringIO/list/str inputs. Whitespace-only value. Leading/trailing tab. Continuation of an empty value. The blank line still stops parsing, so `article()` keeps the body intact. A first-line continuation still raises. Repeated headers still keep the last value (HeaderDict from pairs). |
| Docstring | Matches the code ("unfolded without changing internal whitespace … whole values are trimmed"). |

## Notes (not findings)
- tests/test_utils.py:146: whether the timing test fails on base depends on the host. Base needs about 2.5e11 bytes of
  memcpy (about 20 s at about 12 GB/s), so a fast host could finish under the 10 s limit and the test would pass on base
  there. On the head the margin to 10 s is large, so the test won't be flaky. Only the "fails on base" evidence for this
  one test depends on the host; the whitespace tests carry the fix.
- Behaviour change, as intended: a whitespace-only continuation line (" \t") now adds its whitespace inside the value.
  That's correct per RFC 5322 2.2.3.

## Not checked
No host run. Did not check callers outside nntp/ (none in the package besides article()/head()).
