"""Offline tests for session and connection management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import nntp
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
