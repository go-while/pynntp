Fixed: lines starting with a dot were returned twice (once unstuffed, once raw) by BODY, ARTICLE, HEAD, LIST and the other multi-line commands, which corrupted yEnc bodies (#99).
Fixed: gzip-compressed replies (XFEATURE COMPRESS GZIP) repeated data when the terminator arrived after the compressed stream, and dropped bytes that followed the terminator.
