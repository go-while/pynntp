=== PR #182: post(): split body iterable items at LF before dot-stuffing
head fix/post-body-item-lines 2ddb15b
`_prepare_article()` treated each item of a body iterable as one line. Only CR and NUL were refused, so an LF inside an item passed, and the text after it was neither dot-stuffed nor ended with CRLF:

```python
client.post(headers, [b"x\n.\nQUIT\n"])   # sent "x\n.\nQUIT\r\n"
```

A server that ends lines on a bare LF sees the lone `.` and takes the article as finished early; the rest is read as commands. It happens when an item holds several complete lines, for example a pre-formatted text block.

### Fixed
- Each item of a body iterable is split at LF (`_item_lines()`), so every line is CRLF-terminated and dot-stuffed: the example above is sent as `x\r\n..\r\nQUIT\r\n`.
- An item without a trailing LF still ends a line, and an empty item is still an empty line, as before. `str` and `bytes` bodies already went through line splitting and are unchanged.
- The CR/NUL check runs on the split lines, so it works as before: a CR that is part of a CRLF ending is fine; any other CR, or a NUL, raises `NNTPDataError` before anything is sent.
- The `post()` and `_prepare_article()` docstrings say that each item ends a line and items are split at LF.

### Testing
The new tests cover the example above (exact bytes on the wire, through `post()` and `ihave()`), several lines in one item, empty items and items without LF, and the CR/NUL error paths.

council r1: opus 9.6, sol 10 (round 0: haiku 9, sonnet 9)

🤖 Generated with [Claude Code](https://claude.com/claude-code)


=== PR #183: yEnc: parse keywords in linear time
head fix/yenc-keyword-regex 54751e2
`_KEYWORD_RE` in `nntp/yenc.py` was `(\w+)=(\S*)`. On a long run of word characters with no `=`, `findall` retried `\w+` from every start position, so the cost grew with the square of the line length. A poster's article with a `=ybegin ` line followed by about 64 KB of `a` took about 45 s of CPU in `body()` or `article()` (through `_decode_yenc` and `parse_keywords`). The `=yend` line (through `check_trailer`) is affected the same way.

### Fixed
- The key now starts at a word boundary: `(?<!\w)(\w+)=(\S*)`. A start position inside a word run fails at once, so `parse_keywords()` is linear in the line length.
- Results are the same as before for every line: the old pattern also matched from the start of a word run (an earlier start reaches the same `=`), and that is the only start the new pattern tries.

### Testing
The new tests cover a table of keyword lines (`a-b=c`, `x=1x=2`, `==4 a==5`, `9z=2`, a full `=yend` line), `parse_keywords()` on 64 KiB word runs with a time bound, and a BODY with long `=ybegin` and `=yend` lines.

council r2: opus 9.6, sol 10

🤖 Generated with [Claude Code](https://claude.com/claude-code)


=== PR #185: HEAD and ARTICLE: read the whole response before parsing headers
head fix/head-read-all edbe199
`utils.parse_headers()` stops at the first blank line or at a line that is not a header. `head()` and `article()` parsed the response as it was read, so the rest of the response stayed unread in two cases:

- A server sends a blank line inside a HEAD response. `head()` returned the headers, but the rest was unread. The dropped iterator marked the connection broken, so the next command failed with `NNTPSyncError` even though `head()` had returned normally.
- A header line without a colon, in HEAD or ARTICLE. `NNTPDataError` was raised with the rest unread, and `_data_errors()` marked the connection broken.

### Fixed
- `head()` reads the whole response (HEAD responses are small) and then parses it. Lines after a blank line are read and ignored: the headers before it are returned. A bad header line raises `NNTPDataError` ("Invalid article headers: ...") with the connection still in sync.
- `article()` reads the rest of the response before it raises `NNTPDataError` for a bad header line, so the connection stays in sync there too.
- The docstrings of both methods say this.
- If the connection is lost while the rest is read, the usual error is raised and the connection is marked broken, as before.

### Behaviour change
A bad header line in HEAD or ARTICLE no longer breaks the connection: the next command works. A blank line inside a HEAD response no longer breaks the next command.

### Testing
The new tests cover HEAD with a blank line inside, a line without a colon in HEAD and ARTICLE, and a connection cut off in the middle of the response.

council r2: opus 9.5, sol 10

🤖 Generated with [Claude Code](https://claude.com/claude-code)


=== PR #186: Reject an invalid ssl_mode instead of connecting in plain text
head fix/ssl-context-plaintext 9a3379d
`ssl_mode` was compared only with the two `SSLMode` members. Any other value, such as the string `"STARTTLS"` (upper case) or `"tls"`, took neither TLS branch, even with `use_ssl=True`:

```python
NNTPClient("news.example.com", username="u", password="p", use_ssl=True, ssl_mode="STARTTLS")
```

connected in plain text on port 119 and, on a 480 reply, sent the login and password in clear. The caller had asked for TLS and got no error.

### Fixed
- With `use_ssl=True`, the constructor converts `ssl_mode` with `SSLMode(ssl_mode)` first. An `SSLMode` member or its value (`"implicit"`, `"starttls"`) works as before; anything else raises `ValueError` before a socket is opened. With `use_ssl=False` the mode is not used, so it is not checked.
- The constructor docstrings, the `from_url()` docstring and the README say that `ssl_mode` and `ssl_context` only take effect with `use_ssl=True` (which an `nntps://`, `snews://` or `nntp+starttls://` URL sets), and that an invalid `ssl_mode` raises `ValueError`.

### Behaviour change
With `use_ssl=True`, an invalid `ssl_mode` now raises `ValueError` instead of silently connecting without TLS. Valid values, including the lower-case strings, behave as before. Passing `ssl_context` with `use_ssl=False` or an `nntp://` URL is still accepted and still ignored, so config-driven code that always passes a context keeps working.

### Testing
The new tests cover invalid modes with `use_ssl=True` (no socket is opened), the ignored mode with `use_ssl=False`, the string values, and `from_url()` passing the `ssl_context` on.

council r2: opus 9.5, terra 9.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)


=== PR #171: XZVER/XZHDR: keep a last row without CRLF
head fix/160-xz-last-row 8ac5794
When the compressed XZVER/XZHDR data ended with a row that had no CRLF, `_info_yenczlib()` dropped that row silently, even though the stream was complete and its yEnc size/CRC were correct.

### Fixed
- After the yEnc trailer and the end-of-stream checks pass, a remaining row without CRLF is returned as the last row. No CRLF is added; the row parsers don't need one.
- If the remaining data holds a bare LF (rows not separated by CRLF), it raises `NNTPDataError` instead.
- The line-length, CRC/size and truncation checks are unchanged. If they fail, the partial row isn't returned.

### Merging
#145's known-failure marker for `xzver/last-row-without-crlf` goes when this merges.

### Testing
The new tests cover XZVER and XZHDR with one and two rows whose last row lacks CRLF, terminated rows, an empty compressed stream and a bad trailer.

Fixes #160.

council r1: opus 9.5, sol 9.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)


