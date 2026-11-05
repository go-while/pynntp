Fixed: Closing or quitting an NNTP client more than once is safe. Context managers close without sending QUIT when a reply is active or the block raises, and close the socket even if QUIT fails.
