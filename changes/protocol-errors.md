Fixed: NNTPProtocolError for an invalid status line carries a readable str message instead of bytes, and an empty status line raises it instead of IndexError.
