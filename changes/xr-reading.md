Changed: `article()` detects yEnc from the body (a first line `=ybegin`), as `body()` does, and no longer from the Subject, so a plain-text article whose Subject mentions yEnc is returned unchanged; forced decoding (`decode=True`) of a body without `=ybegin` raises `NNTPDataError`.
Fixed: a malformed article number in the 220 reply to ARTICLE left the article on the connection; it is now read and dropped and `NNTPProtocolError` is raised (also for an empty 220 line, which raised `IndexError`).
Fixed: a decoding error from an `info()` reply (with `errors="strict"`) kept the reply active while the exception was held.
Fixed: an XZVER/XZHDR reply whose compressed data was cut short returned partial rows; a partial last line now raises `NNTPDataError`.
Fixed: status codes must be exactly three digits; `+111`, `0111` or `1_11` raise `NNTPProtocolError`.
