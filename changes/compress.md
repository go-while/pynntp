Added: compress() enables RFC 8054 DEFLATE compression; authentication, STARTTLS and MODE READER are prohibited after activation.
Changed: INN 2.6 nnrpd may stall on compressed POST or IHAVE input; avoid enabling compression for uploads to those servers.
