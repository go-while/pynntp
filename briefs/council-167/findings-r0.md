# Round-0 findings on #167 (head 54cb6e0), for the cross-check

From Sonnet:
- S1 (Low, new) test_inn2.py:406-410 test_article_in_empty_group: the default-path assert no longer requires INN's exact (0, 1, 0, "junk"); it accepts every "empty" form, including a client bug returning 0 0 0 and impossible values like 5/3. RFC 3977 6.1.1.2: only high = low - 1 may be below low; the third form is high >= low. Fix: assert high == low - 1 or all zeros; drop "high below low" from comment and PR text.
- S2 (Low, new) test_inn2.py ~440 test_xover_full_field: calls XOVER but is gated on require_listed("OVER"); a server with OVER but no XOVER fails instead of skipping; one with XOVER but no OVER skips.
- S3 (Low, new) test_inn2.py ~588-600 test_from_url and client(): ports are always passed explicitly, so the default-port choice (nntps -> 563, nntp -> 119) is no longer exercised against a real server (unit tests cover it with mocks).

From Haiku:
- H1 (Low, new) test_inn2.py:402-409 test_article_in_empty_group: same as S1 (default INN run used to assert the exact reply).
- H2 (Low, new) test_inn2.py:438/442 test_newnews: the default INN run used the wildmat "local.*" (matched local.general and local.test); now the group only, so the wildcard form is no longer exercised by default. Fix for H1/H2: keep the exact INN checks on the default path; use the relaxed form only when PYNNTP_HOST is set.

From Luna:
- L1 (Low, new) test_inn2.py:571 (refused-login test): with a server where the configured credentials are user/secret and accepted, the test's supposedly rejected login can succeed, so the test fails at pytest.raises: a wrong failure verdict for a valid credential configuration.
