Fixed: Commands and AUTHINFO credentials containing CR, LF or NUL now raise ValueError before being sent, preventing command injection.
