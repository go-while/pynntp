Fixed: a read timeout raises NNTPTimeoutError (an NNTPError and a TimeoutError) instead of a bare TimeoutError, and closes the connection, since the late reply would be taken for the next command.
