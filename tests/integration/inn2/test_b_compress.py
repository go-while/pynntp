"""COMPRESS negotiation against disposable INN."""

import ssl

import pytest

import nntp
from nntp.types import SSLMode
from tests.integration.portable import TLS_CAFILE, require


@pytest.mark.parametrize("mode", [None, SSLMode.STARTTLS, SSLMode.IMPLICIT])
def test_compress_round_trip(mode: SSLMode | None) -> None:
    require("COMPRESS")
    if mode == SSLMode.STARTTLS:
        require("STARTTLS")
    port = 563 if mode == SSLMode.IMPLICIT else 119
    context = ssl.create_default_context(cafile=TLS_CAFILE)
    with nntp.NNTPClient(
        "localhost",
        port,
        use_ssl=mode is not None,
        ssl_mode=mode or SSLMode.IMPLICIT,
        ssl_context=context,
    ) as client:
        assert any(
            line.startswith("COMPRESS DEFLATE") for line in client.capabilities()
        )
        client.compress()
        assert client.compressed
        assert client.date().tzinfo is not None
        assert any(
            group.name == "local.test" for group in client.list_active("local.*")
        )
        with pytest.raises(nntp.NNTPError, match="compress"):
            client.mode_reader()
