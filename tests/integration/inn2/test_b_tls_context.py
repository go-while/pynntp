"""TLS context behavior against the disposable INN test server."""

import ssl

import pytest

import nntp
from nntp.types import SSLMode
from tests.integration.portable import TLS_CAFILE, require


@pytest.mark.parametrize("mode", [SSLMode.IMPLICIT, SSLMode.STARTTLS])
def test_custom_tls_context(mode: SSLMode, monkeypatch: pytest.MonkeyPatch) -> None:
    # The test server's self-signed certificate is trusted explicitly. The
    # context must not be weakened by the insecure environment setting.
    if mode == SSLMode.STARTTLS:
        require("STARTTLS")
    context = ssl.create_default_context(cafile=TLS_CAFILE)
    monkeypatch.setenv("PYNNTP_TLS_INSECURE", "1")
    port = 563 if mode == SSLMode.IMPLICIT else 119
    with nntp.NNTPClient(
        "localhost", port, use_ssl=True, ssl_mode=mode, ssl_context=context
    ) as client:
        assert client.date().tzinfo is not None
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_custom_context_not_weakened_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = ssl.create_default_context()
    monkeypatch.setenv("PYNNTP_TLS_INSECURE", "1")
    with pytest.raises(ssl.SSLCertVerificationError):
        nntp.NNTPClient("localhost", 563, use_ssl=True, ssl_context=context)
