# Council R1 — 7: fix/headerdict-copy

Reviewer: pynntp-sol, OpenAI GPT-6.1 Sol. **Score: 8/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Head: `3a216cf8e5edddc943a924f3c0a29ddde0480cb2`.

Known-item check: read upstream #166 plus open issues and PRs. This slot-state
loss is not in that inventory. **Classification: new in this change.**

| Severity | Head file:line | Function | What goes wrong | Trigger | Who |
|---|---|---|---|---|---|
| Low | `nntp/headerdict.py:86–92` | `HeaderDict.copy` / `__copy__` | A subclass's slotted instance attributes disappear. The returned object retains the subclass type but its slots are uninitialized; using the metadata raises AttributeError or loses state. copy.copy now dispatches here, so this also regresses existing shallow-copy behavior for such subclasses. | A HeaderDict subclass uses `__slots__ = ("article_number",)` for per-article metadata, sets it, then calls copy.copy(instance) or the new .copy(). | Ordinary caller using a slotted mapping subclass; no malformed article or hostile server needed. |

Minimal trigger (review data; **not executed locally**):

```python
import copy
from nntp.headerdict import HeaderDict

class TaggedHeaders(HeaderDict):
    __slots__ = ("article_number",)

h = TaggedHeaders(Subject="hello")
h.article_number = 42
duplicate = copy.copy(h)
duplicate.article_number  # AttributeError at this head
```

Source proof: the copy returns successfully, silently omitting initialized
metadata; AttributeError appears only when a caller later accesses it.
Slot values reside in slot descriptors, not h.__dict__. The new
implementation allocates without __init__, copies only __dict__ and _items,
and returns the object without setting those descriptors. This contradicts
the method's explicit promise to preserve subclass instance attributes. The
base copy.copy protocol includes slot state; the added __copy__ bypasses it.
The submitted subclass test uses only __dict__ attributes, so misses this case.

The normal HeaderDict mapping copy is otherwise correct: _items becomes an
independent dict, and its string/tuple contents can safely be shared shallowly.
Preserve both dict and slot state while detaching _items; no broader copying
feature request is intended.

Verification: source-verified state omission; optional VM reproduction not run.
No tree edits, commits, installs or GitHub writes. G1 observed.

7 fix/headerdict-copy: 8, 1 findings (0H/0M/1L)
