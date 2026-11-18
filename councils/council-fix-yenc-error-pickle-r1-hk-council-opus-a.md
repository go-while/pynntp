# fix/yenc-error-pickle (a0e15a7) — hk-council-opus-a
Score: 9

No findings. __reduce__ rebuilds the error with cls(message, data) and restores __dict__ (data and __notes__). __cause__ and the traceback are dropped, but plain BaseException pickling drops them too. Not verified on a host.
