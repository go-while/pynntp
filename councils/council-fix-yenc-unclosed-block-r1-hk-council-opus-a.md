# fix/yenc-unclosed-block (2cf7f35) — hk-council-opus-a
Score: 9

No findings. A second =ybegin while a block is open now records 'missing =yend trailer'; the decoded data still gets returned in NNTPYEncError.data. Not verified on a host (read-only review).
