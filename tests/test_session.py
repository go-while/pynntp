"""Offline tests for session and connection management."""

from __future__ import annotations

import contextlib
import socket
import ssl
from typing import TYPE_CHECKING
from unittest import mock

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


def test_repeated_480_does_not_recurse(scripted_server: Start) -> None:
    dates = iter([b"480 authenticate\r\n"] * 3 + [b"111 20260102030405\r\n"])
    server = scripted_server(
        {
            "DATE": lambda _line: next(dates),
            "AUTHINFO USER user": b"381 password required\r\n",
            "AUTHINFO PASS pass": b"281 accepted\r\n",
        }
    )
    client = server.client(username="user", password="pass")  # noqa: S106
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        client.date()
    assert server.received == [
        "MODE READER",
        "DATE",
        "AUTHINFO USER user",
        "AUTHINFO PASS pass",
        "DATE",
    ]


def test_480_without_username_sends_no_authinfo(scripted_server: Start) -> None:
    server = scripted_server({"DATE": b"480 authenticate\r\n"})
    client = server.client()
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        client.date()
    assert server.received == ["MODE READER", "DATE"]


def test_login_explicit_and_stored_credentials(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "AUTHINFO USER stored": b"381 password required\r\n",
            "AUTHINFO PASS secret": b"281 accepted\r\n",
            "AUTHINFO USER other": b"281 accepted\r\n",
        }
    )
    client = server.client(username="stored", password="secret")  # noqa: S106
    client.login()
    client.login("other", "unused")
    assert server.received == [
        "MODE READER",
        "AUTHINFO USER stored",
        "AUTHINFO PASS secret",
        "AUTHINFO USER other",
    ]


def test_483_requires_encryption_without_authinfo(scripted_server: Start) -> None:
    server = scripted_server({"DATE": b"483 encryption required\r\n"})
    client = server.client(username="user", password="pass")  # noqa: S106
    with pytest.raises(nntp.NNTPTemporaryError, match="483"):
        client.date()
    assert server.received == ["MODE READER", "DATE"]


def test_mode_reader_authenticates_without_retry(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "MODE READER": b"480 authenticate\r\n",
            "AUTHINFO USER user": b"381 password required\r\n",
            "AUTHINFO PASS pass": b"281 accepted\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(username="user", password="pass")  # noqa: S106
    assert client.date().year == 2026
    assert server.received == [
        "MODE READER",
        "AUTHINFO USER user",
        "AUTHINFO PASS pass",
        "DATE",
    ]


@pytest.mark.parametrize(("verb", "args"), [("MODE", "READER"), ("MODE  READER", None)])
def test_raw_mode_reader_challenge_does_not_authenticate_or_retry(
    scripted_server: Start, verb: str, args: str | None
) -> None:
    command = f"{verb} {args}" if args else verb
    server = scripted_server(
        {
            command: b"480 authentication required\r\n",
            "AUTHINFO USER user": b"281 accepted\r\n",
        }
    )
    client = server.client(reader=False, username="user")
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        client.command(verb, args)
    assert server.received == [command]


def test_authinfo_challenge_does_not_recurse(scripted_server: Start) -> None:
    server = scripted_server({"AUTHINFO USER user": b"480 authenticate\r\n"})
    client = server.client(username="user", password="pass")  # noqa: S106
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        client.login()
    assert server.received == ["MODE READER", "AUTHINFO USER user"]


def test_authinfo_pass_failure_does_not_retry(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "DATE": b"480 authenticate\r\n",
            "AUTHINFO USER user": b"381 password required\r\n",
            "AUTHINFO PASS pass": b"481 rejected\r\n",
        }
    )
    client = server.client(username="user", password="pass")  # noqa: S106
    with pytest.raises(nntp.NNTPTemporaryError, match="481"):
        client.date()
    assert server.received == [
        "MODE READER",
        "DATE",
        "AUTHINFO USER user",
        "AUTHINFO PASS pass",
    ]


def test_mode_reader_challenge_without_username_does_not_authenticate(
    scripted_server: Start,
) -> None:
    server = scripted_server({"MODE READER": b"480 authenticate\r\n"})
    with pytest.raises(nntp.NNTPTemporaryError, match="480"):
        server.client()
    assert server.received == ["MODE READER"]


def test_login_without_username_fails_locally(scripted_server: Start) -> None:
    server = scripted_server()
    client = server.client()
    with pytest.raises(nntp.NNTPError, match="username"):
        client.login()
    assert server.received == ["MODE READER"]


def test_login_does_not_interrupt_active_reply(scripted_server: Start) -> None:
    server = scripted_server({"CAPABILITIES": b"101 caps\r\nVERSION 2\r\n.\r\n"})
    client = server.client(username="user", password="pass")  # noqa: S106
    capabilities = client.capabilities()
    assert next(capabilities) == "VERSION 2"
    with pytest.raises(nntp.nntp.NNTPSyncError):
        client.login()
    assert server.received == ["MODE READER", "CAPABILITIES"]
    assert list(capabilities) == []


@pytest.mark.parametrize("invalid", ["\r", "\n", "\0"])
@pytest.mark.parametrize("in_verb", [True, False])
def test_command_rejects_control_injection(
    scripted_server: Start, invalid: str, *, in_verb: bool
) -> None:
    server = scripted_server({"DATE": b"111 20260102030405\r\n"})
    client = server.client()
    verb = f"GROUP{invalid}POST" if in_verb else "GROUP"
    args = "local.test" if in_verb else f"local.test{invalid}POST"
    with pytest.raises(ValueError, match="CR, LF or NUL"):
        client.command(verb, args)
    assert client.date().year == 2026
    assert server.received == ["MODE READER", "DATE"]


@pytest.mark.parametrize("invalid", ["\r", "\n", "\0"])
@pytest.mark.parametrize("in_username", [True, False])
def test_login_rejects_invalid_credentials_before_authinfo(
    scripted_server: Start, invalid: str, *, in_username: bool
) -> None:
    server = scripted_server({"DATE": b"111 20260102030405\r\n"})
    client = server.client()
    username = f"user{invalid}DATE" if in_username else "user"
    password = "pass" if in_username else f"pass{invalid}DATE"
    with pytest.raises(ValueError, match="CR, LF or NUL"):
        client.login(username, password)
    assert client.date().year == 2026
    assert server.received == ["MODE READER", "DATE"]


def test_automatic_login_preflights_both_credentials(scripted_server: Start) -> None:
    dates = iter([b"480 authenticate\r\n", b"111 20260102030405\r\n"])
    server = scripted_server({"DATE": lambda _line: next(dates)})
    client = server.client(username="user", password="pass\nDATE")  # noqa: S106
    with pytest.raises(ValueError, match="CR, LF or NUL"):
        client.date()
    assert client.date().year == 2026
    assert server.received == ["MODE READER", "DATE", "DATE"]


@pytest.mark.parametrize(
    ("setting", "insecure"),
    [("0", False), ("false", False), ("", False), ("1", True), ("yes", True)],
)
def test_tls_insecure_environment_values(
    scripted_server: Start,
    monkeypatch: pytest.MonkeyPatch,
    setting: str,
    *,
    insecure: bool,
) -> None:
    context = ssl.create_default_context()
    monkeypatch.setenv("PYNNTP_TLS_INSECURE", setting)
    monkeypatch.setattr(ssl, "create_default_context", lambda: context)
    monkeypatch.setattr(context, "wrap_socket", lambda sock, **_kwargs: sock)
    client = scripted_server().client(use_ssl=True)
    assert context.check_hostname is not insecure
    assert context.verify_mode == (ssl.CERT_NONE if insecure else ssl.CERT_REQUIRED)
    client.close()


def test_explicit_tls_context_is_used_without_mutation(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = ssl.create_default_context()
    monkeypatch.setenv("PYNNTP_TLS_INSECURE", "1")
    wrapped: list[str] = []

    def wrap(sock: socket.socket, *, server_hostname: str) -> socket.socket:
        wrapped.append(server_hostname)
        return sock

    monkeypatch.setattr(context, "wrap_socket", wrap)
    client = scripted_server().client(use_ssl=True, ssl_context=context)
    assert wrapped == ["127.0.0.1"]
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED
    client.close()


def test_timeout_and_sync_errors_are_exported() -> None:
    assert issubclass(nntp.NNTPTimeoutError, nntp.NNTPError)
    assert issubclass(nntp.NNTPTimeoutError, TimeoutError)
    assert issubclass(nntp.NNTPSyncError, nntp.NNTPError)


def test_connect_timeout_is_nntp_and_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def connect(*_args: object, **_kwargs: object) -> socket.socket:
        raise TimeoutError("connect timed out")

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(nntp.NNTPTimeoutError) as error:
        nntp.NNTPClient("localhost")
    assert isinstance(error.value, TimeoutError)
    assert isinstance(error.value.__cause__, TimeoutError)


def test_send_timeout_is_nntp_and_timeout_error(scripted_server: Start) -> None:
    server = scripted_server()
    client = server.client()
    real_socket = client.socket
    fake = mock.Mock(wraps=real_socket)
    fake.sendall.side_effect = TimeoutError("send timed out")
    client.socket = fake
    try:
        with pytest.raises(nntp.NNTPTimeoutError) as error:
            client.date()
        assert isinstance(error.value, TimeoutError)
        assert isinstance(error.value.__cause__, TimeoutError)
        assert real_socket.fileno() == -1
    finally:
        client.close()


@pytest.mark.parametrize("mode", [SSLMode.IMPLICIT, SSLMode.STARTTLS])
def test_tls_timeout_is_nntp_and_timeout_error(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, mode: SSLMode
) -> None:
    context = ssl.create_default_context()
    sockets: list[socket.socket] = []

    def wrap(sock: socket.socket, **_kwargs: object) -> socket.socket:
        sockets.append(sock)
        raise TimeoutError("handshake timed out")

    monkeypatch.setattr(context, "wrap_socket", wrap)
    server = scripted_server({"STARTTLS": b"382 ready\r\n"})
    with pytest.raises(nntp.NNTPTimeoutError) as error:
        server.client(use_ssl=True, ssl_mode=mode, ssl_context=context)
    assert isinstance(error.value, TimeoutError)
    assert isinstance(error.value.__cause__, TimeoutError)
    assert sockets[0].fileno() == -1


def test_closed_socket_reports_nntp_error(scripted_server: Start) -> None:
    client = scripted_server().client()
    client.close()
    with pytest.raises(nntp.NNTPError, match="closed"):
        client.date()


def test_empty_password_after_381_is_not_sent(scripted_server: Start) -> None:
    server = scripted_server({"AUTHINFO USER user": b"381 password required\r\n"})
    client = server.client(username="user")
    with pytest.raises(nntp.NNTPError, match="password"):
        client.login()
    assert server.received == ["MODE READER", "AUTHINFO USER user"]


def test_unexpected_capabilities_block_is_drained(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"215 list\r\nline\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPReplyError):
        list(client.capabilities())
    assert client.date().year == 2026


def test_capabilities_is_eager_and_held_reply_blocks(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"101 capabilities\r\nVERSION 2\r\nREADER\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    reply = client.capabilities()
    assert server.received == ["MODE READER", "CAPABILITIES"]
    with pytest.raises(nntp.NNTPSyncError):
        client.date()
    assert list(reply) == ["VERSION 2", "READER"]
    assert client.date().year == 2026


@pytest.mark.parametrize("read_first", [False, True])
def test_capabilities_close_releases_reply(
    scripted_server: Start, *, read_first: bool
) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"101 caps\r\nVERSION 2\r\nREADER\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    reply = client.capabilities()
    assert server.received == ["MODE READER", "CAPABILITIES"]
    if read_first:
        assert next(reply) == "VERSION 2"
    reply.close()  # type: ignore[attr-defined]
    assert client.date().year == 2026


def test_dropped_unread_capabilities_drains_before_next_command(
    scripted_server: Start,
) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"101 caps\r\nVERSION 2\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    reply = client.capabilities()
    assert server.received == ["MODE READER", "CAPABILITIES"]
    del reply
    assert client.date().year == 2026


def test_capabilities_status_failure_is_eager(scripted_server: Start) -> None:
    server = scripted_server({"CAPABILITIES": b"500 unsupported\r\n"})
    client = server.client()
    with pytest.raises(nntp.NNTPPermanentError):
        client.capabilities()
    assert server.received == ["MODE READER", "CAPABILITIES"]


def test_capabilities_decode_failure_releases_retained_traceback(
    scripted_server: Start,
) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"101 caps\r\n\xff\r\nREADER\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    client.errors = "strict"
    reply = client.capabilities()
    with pytest.raises(UnicodeDecodeError) as error:
        next(reply)
    assert error.value.__traceback__ is not None
    assert client.date().year == 2026


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
