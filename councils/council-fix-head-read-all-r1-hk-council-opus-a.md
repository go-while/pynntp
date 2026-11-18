# fix/head-read-all (edbe199) — hk-council-opus-a
Score: 9

No findings. article() drains the raw iterator after a header ValueError (UnicodeDecodeError is a subclass, so it is covered). head() buffers the whole HEAD response before parsing; HEAD responses are small, so this is acceptable. Not verified on a host.
