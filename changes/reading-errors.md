Changed: article() and head() raise NNTPDataError instead of ValueError when the article headers cannot be parsed; the connection stays usable.
Fixed: a yEnc trailer with a non-numeric part= value was accepted.
