"""Offline tests for session and connection management."""

from __future__ import annotations

import contextlib
import socket
from typing import TYPE_CHECKING

import pytest

import nntp
from nntp.types import SSLMode
from tests.scripted import CLOSE

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.scripted import ScriptedServer

    Start = Callable[..., ScriptedServer]


@pytest.mark.parametrize("first", ["close", "quit"])
def test_repeated_close_and_quit(scripted_server: Start, first: str) -> None:
    server = scripted_server()
    with server.client() as client:
        getattr(client, first)()
        client.quit()
        client.close()
        client.quit()
    assert client.socket.fileno() == -1
    assert server.received == ["MODE READER"] + (["QUIT"] if first == "quit" else [])


@pytest.mark.parametrize(
    ("greeting", "script", "kwargs"),
    [
        (b"500 greeting failed\r\n", {}, {}),
        (b"202 unexpected greeting\r\n", {}, {}),
        (
            b"200 ready\r\n",
            {"STARTTLS": b"580 TLS failed\r\n"},
            {"use_ssl": True, "ssl_mode": SSLMode.STARTTLS},
        ),
        (
            b"200 ready\r\n",
            {"STARTTLS": b"200 unexpected\r\n"},
            {"use_ssl": True, "ssl_mode": SSLMode.STARTTLS},
        ),
        (b"200 ready\r\n", {"MODE READER": b"500 reader failed\r\n"}, {}),
        (b"200 ready\r\n", {"MODE READER": b"202 unexpected\r\n"}, {}),
    ],
)
def test_initialization_failure_closes_socket(
    scripted_server: Start,
    monkeypatch: pytest.MonkeyPatch,
    greeting: bytes,
    script: dict[str, bytes],
    kwargs: dict[str, object],
) -> None:
    server = scripted_server(script, greeting=greeting)
    real_connect = socket.create_connection
    opened: list[socket.socket] = []

    def connect(address: tuple[str, int], timeout: float) -> socket.socket:
        sock = real_connect(address, timeout)
        opened.append(sock)
        return sock

    monkeypatch.setattr(socket, "create_connection", connect)
    try:
        with pytest.raises(nntp.NNTPError):
            server.client(**kwargs)
        assert len(opened) == 1
        assert opened[0].fileno() == -1
    finally:
        for sock in opened:
            sock.close()


@pytest.mark.parametrize("mode", [SSLMode.IMPLICIT, SSLMode.STARTTLS])
def test_tls_handshake_failure_closes_socket(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, mode: SSLMode
) -> None:
    server = scripted_server({"STARTTLS": b"382 begin TLS\r\n"})
    opened: list[socket.socket] = []

    def fail_handshake(client: nntp.BaseNNTPClient, _host: str) -> None:
        opened.append(client.socket)
        raise OSError("handshake failed")

    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", fail_handshake)
    try:
        with pytest.raises(OSError, match="handshake failed"):
            server.client(use_ssl=True, ssl_mode=mode)
        assert len(opened) == 1
        assert opened[0].fileno() == -1
    finally:
        for sock in opened:
            sock.close()


@pytest.mark.parametrize("reader", [True, False])
def test_starttls_orders_reader_and_discards_plaintext(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, reader: bool
) -> None:
    server = scripted_server(
        {
            "STARTTLS": b"382 begin TLS\r\n111 19990101000000\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    handshakes: list[str] = []

    def fake_tls(client: nntp.BaseNNTPClient, host: str) -> None:
        assert client._buffer.read() == b""  # noqa: SLF001
        handshakes.append(host)

    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", fake_tls)
    client = server.client(use_ssl=True, ssl_mode=SSLMode.STARTTLS, reader=reader)
    assert handshakes == ["127.0.0.1"]
    assert server.received == (["MODE READER"] if reader else []) + ["STARTTLS"]
    assert client.date().year == 2026
    client.quit()


def test_starttls_reader_precedes_upgrade(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = scripted_server({"STARTTLS": b"382 begin TLS\r\n"})
    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", lambda *_: None)
    client = server.client(use_ssl=True, ssl_mode=SSLMode.STARTTLS)
    assert server.received == ["MODE READER", "STARTTLS"]
    client.quit()


def test_base_starttls_does_not_request_reader(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = scripted_server({"STARTTLS": b"382 begin TLS\r\n"})
    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", lambda *_: None)
    client = nntp.BaseNNTPClient(
        "127.0.0.1", server.port, use_ssl=True, ssl_mode=SSLMode.STARTTLS
    )
    try:
        assert server.received == ["STARTTLS"]
    finally:
        client.close()


def test_starttls_does_not_authenticate_in_plaintext(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    modes = iter([b"480 authentication required\r\n", b"200 ready\r\n"])
    server = scripted_server(
        {
            "MODE READER": lambda _line: next(modes),
            "AUTHINFO USER user": b"381 password needed\r\n",
            "AUTHINFO PASS pass": b"281 accepted\r\n",
            "STARTTLS": b"382 begin TLS\r\n",
        }
    )
    before_tls: list[str] = []

    def enable_tls(_client: nntp.BaseNNTPClient, _host: str) -> None:
        before_tls.extend(server.received)

    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", enable_tls)
    # Failing closed is acceptable; disclosing credentials before TLS isn't.
    with contextlib.suppress(nntp.NNTPError):
        server.client(
            username="user",
            password="pass",  # noqa: S106 (dummy scripted-server credential)
            use_ssl=True,
            ssl_mode=SSLMode.STARTTLS,
        )
    assert not any(
        line.startswith("AUTHINFO") for line in (before_tls or server.received)
    )


@pytest.mark.parametrize("response", [b"480 authenticate\r\n", b"483 use TLS\r\n"])
def test_starttls_reader_auth_is_deferred(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, response: bytes
) -> None:
    dates = iter([b"480 authenticate\r\n", b"111 20260102030405\r\n"])
    server = scripted_server(
        {
            "MODE READER": response,
            "STARTTLS": b"382 begin TLS\r\n",
            "DATE": lambda _line: next(dates),
            "AUTHINFO USER user": b"381 password required\r\n",
            "AUTHINFO PASS pass": b"281 accepted\r\n",
        }
    )
    before_tls: list[str] = []

    def enable_tls(_client: nntp.BaseNNTPClient, _host: str) -> None:
        before_tls.extend(server.received)

    monkeypatch.setattr(nntp.BaseNNTPClient, "_enable_tls", enable_tls)
    client = server.client(
        username="user",
        password="pass",  # noqa: S106 (dummy test credential)
        use_ssl=True,
        ssl_mode=SSLMode.STARTTLS,
    )
    assert before_tls == ["MODE READER", "STARTTLS"]
    assert client.date().year == 2026
    assert server.received == [
        "MODE READER",
        "STARTTLS",
        "DATE",
        "AUTHINFO USER user",
        "AUTHINFO PASS pass",
        "DATE",
    ]
    client.close()


@pytest.mark.parametrize("base", [True, False])
def test_starttls_auth_challenge_never_sends_credentials(
    scripted_server: Start, base: bool
) -> None:
    server = scripted_server({"STARTTLS": b"480 authenticate\r\n"})
    cls = nntp.BaseNNTPClient if base else nntp.NNTPClient
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        cls(
            "127.0.0.1",
            server.port,
            username="user",
            password="pass",  # noqa: S106 (dummy test credential)
            use_ssl=True,
            ssl_mode=SSLMode.STARTTLS,
        )
    assert server.received == ([] if base else ["MODE READER"]) + ["STARTTLS"]


def test_exception_closes_without_quit(scripted_server: Start) -> None:
    server = scripted_server()
    with pytest.raises(ValueError, match="user exception"), server.client() as client:
        raise ValueError("user exception")
    assert client.socket.fileno() == -1
    assert server.received == ["MODE READER"]


def test_close_error_does_not_mask_user_exception(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = scripted_server()
    client = server.client()

    def failing_close() -> None:
        client.socket.close()
        raise OSError("close failed")

    monkeypatch.setattr(client, "close", failing_close)
    with pytest.raises(ValueError, match="user exception"), client:
        raise ValueError("user exception")
    assert client.socket.fileno() == -1
    assert server.received == ["MODE READER"]


def test_close_error_does_not_fail_successful_context(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = scripted_server()
    client = server.client()

    def failing_close() -> None:
        client.socket.close()
        raise OSError("close failed")

    monkeypatch.setattr(client, "close", failing_close)
    with client:
        pass
    assert client.socket.fileno() == -1


def test_active_reply_closes_without_quit(scripted_server: Start) -> None:
    server = scripted_server(
        {"CAPABILITIES": b"101 capabilities\r\nVERSION 2\r\n.\r\n"}
    )
    with server.client() as client:
        reply = client.capabilities()
        assert next(reply) == "VERSION 2"
    assert client.socket.fileno() == -1
    assert server.received == ["MODE READER", "CAPABILITIES"]


def test_reply_state_error_during_exit_closes_socket(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = scripted_server()
    client = server.client()

    def failed_drain(_client: nntp.NNTPClient) -> bool:
        raise TimeoutError("reply drain timed out")

    monkeypatch.setattr(
        type(client), "_generating", property(failed_drain), raising=False
    )
    with client:
        pass
    assert client.socket.fileno() == -1
    assert server.received == ["MODE READER"]


@pytest.mark.parametrize(
    "reply", [CLOSE, b"400 unavailable\r\n", [1.0, b"205 bye\r\n"]]
)
def test_quit_failure_still_closes(scripted_server: Start, reply: object) -> None:
    server = scripted_server({"QUIT": reply})
    client = server.client()
    client.socket.settimeout(0.05)
    with pytest.raises((nntp.NNTPError, OSError)):
        client.quit()
    assert client.socket.fileno() == -1
    client.quit()


@pytest.mark.parametrize(
    "reply", [CLOSE, b"400 unavailable\r\n", [1.0, b"205 bye\r\n"]]
)
def test_context_quit_failure_still_closes(
    scripted_server: Start, reply: object
) -> None:
    server = scripted_server({"QUIT": reply})
    with server.client() as client:
        client.socket.settimeout(0.05)
    assert client.socket.fileno() == -1
