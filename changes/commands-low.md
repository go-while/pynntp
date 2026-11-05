Fixed: Overview fields marked `:full` have their field-name prefix removed, while empty optional fields and trailing value whitespace are preserved. The public `overview_fmt` tuple remains unchanged.
Fixed: Invalid DATE and newsgroup response data raises `NNTPDataError` instead of leaking parser `ValueError`; standalone utility parsers keep their existing `ValueError` API.
Changed: LIST EXTENSIONS is documented as an obsolete legacy command requiring status `202`; unsupported-server errors such as INN's `501` are still propagated. Use CAPABILITIES for RFC 3977 discovery.
