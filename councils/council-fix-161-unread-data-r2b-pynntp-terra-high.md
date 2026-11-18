# Council r2b: fix/161-unread-data

- **Head:** `976d46ee0f8687857d9334f273c4d1ae6594c229`; base `2bfca175d31d1a78360c1df5e1d3cdbc739ed86f`.
- **Score:** 9.5/10. **Findings:** 0 (H/M/L: 0/0/0).
- **Review by reading:** the new check runs within `_sync()` before command bytes are sent and before article bytes follow a ready reply; a detected extra byte marks the connection broken. Under COMPRESS it first drains pending inflater output without treating an empty flush as a reply. Reviewed greeting, automatic authentication, normal and error replies, multi-line/gzip/XZ paths, reconnect, COMPRESS activation and POST/IHAVE interactions, plus the changed packet-aware fake socket.
- **Notes, not findings:** the check only covers bytes already in the client buffer or inflater; extra server bytes that arrive later can still be mistaken for the next reply. This is an explicitly limited mitigation of the already-known #161, not a newly introduced defect or a guarantee about future reads.
- **Prior context:** I previously reviewed the project's session area; I do not recall a prior review finding about this particular change.
- **Not checked:** no tests, probes, real server connections, integration matrix or CI results; no branches or GitHub state were modified. This is a reading review, not a claim that tests passed.

10 fix/161-unread-data: 9.5, 0 findings (0/0/0); below 9.5 because: -
