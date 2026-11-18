# fix/reconnect-failure-broken (0ae1bd3) — hk-council-opus-a
Score: 9

No findings. When create_connection fails inside reconnect(), _broken stays True from close() (nntp.py:788). A failure after the socket opens goes through the except/close() path. On the first connect the object is never built, so _broken being unset there does not matter. Not verified on a host.
