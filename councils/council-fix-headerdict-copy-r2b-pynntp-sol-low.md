# Council R2b — 7: fix/headerdict-copy

Reviewer: pynntp-sol-low (OpenAI GPT-6.1 Sol). **Score: 10/10.**
Base: `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
Reviewed head: `8f63cdb265cb4eb484b61f8ca9be80e6be5f4c1b`.
Scope: the whole copy implementation and tests at this head.
Earlier review reports were not consulted.

## Findings

None. No remaining new defect meeting the Findings test identified.

## Code evidence

`nntp/headerdict.py:87–98` allocates the same concrete type, restores dictionary
state and initialized slots from object.__getstate__(), then replaces _items
with an independent dictionary. Consequently mapping updates/deletions cannot
affect the original, while the immutable stored strings/tuples may be shared.
Slot restoration includes the case where dictionary state is absent/None.
Unset slots remain unset.

Python3.11 is the project's minimum, so object.__getstate__ and typing.Self
are available. Ordinary subclass metadata is shallowly shared as documented.
Deepcopy continues through the normal reconstruction protocol rather than
being replaced by the shallow-copy implementation.

Tests cover name spelling/order, mutation independence in both directions,
ordinary/slotted subclasses, unset slots, pickle and deep-copying mutable slot
contents. The visible missing-slot-state problem is addressed in this head;
no claim about an older review verdict is needed to establish that.

## Notes — not findings

No actionable non-finding notes; no requests for a general custom-serialization
framework for arbitrary subclass hooks.

## Verification and limits

Source-verified state handling only. I did not execute copy/pickle tests,
independently run the lead's checks or check an external application's subclass.
No tree edits, commits, installs, host jobs or GitHub writes. G1 observed.

7 fix/headerdict-copy: 10, 0 findings (0H/0M/0L); below 9.5 because: -
