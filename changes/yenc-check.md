Changed: yEnc bodies (body(), article()) are checked against the size and CRC (pcrc32, or crc32 for single-part posts) in their =yend trailer; a mismatch or a missing trailer raises NNTPDataError instead of returning corrupt data (#99 follow-up).
Fixed: text after the =yend trailer of a yEnc body was decoded as data.
