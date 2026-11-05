Fixed: HDR, XHDR and XZHDR values no longer contain trailing wire CRLF; trailing spaces and tabs in a value are preserved.
Fixed: XHDR and XZHDR accept the Message-ID form. An echoed identifier matching the requested Message-ID is normalized to article number `0`, matching HDR and preserving the `(int, str)` result shape; unrelated nonnumeric identifiers still raise `NNTPDataError`.
