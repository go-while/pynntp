Fixed: A zero or false PYNNTP_TLS_INSECURE value no longer disables certificate checks; supplied SSL contexts are used unchanged.
Fixed: Connection, TLS handshake and command-send timeouts raise NNTPTimeoutError (also a TimeoutError); send timeouts close the uncertain connection.
Fixed: Closed connections and missing authentication passwords report NNTPError, and unexpected multi-line CAPABILITIES responses are drained.
Added: Optional ssl_context on clients, and exported NNTPSyncError and NNTPTimeoutError.
