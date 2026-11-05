"""Smoke tests for the scripted-server fixture itself."""

from __future__ import annotations

import contextlib
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

import nntp
from tests.scripted import CLOSE, ReadArticle, ScriptedServer

if TYPE_CHECKING:
    from collections.abc import Callable


def test_date_and_quit(scripted_server: Callable[..., ScriptedServer]) -> None:
    server = scripted_server({"DATE": b"111 20260102030405\r\n"})
    client = server.client()
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    client.quit()
    assert server.received == ["MODE READER", "DATE", "QUIT"]


def test_exact_line_wins_over_verb(
    scripted_server: Callable[..., ScriptedServer],
) -> None:
    server = scripted_server(
        {
            "GROUP local.test": b"211 2 1 2 local.test\r\n",
            "GROUP": b"411 no such group\r\n",
        }
    )
    client = server.client()
    assert client.group("local.test") == (2, 1, 2, "local.test")
    with pytest.raises(nntp.NNTPTemporaryError):
        client.group("other")


def test_split_reply(scripted_server: Callable[..., ScriptedServer]) -> None:
    server = scripted_server(
        {"HELP": [b"100 help\r\nline o", 0.05, b"ne\r\n", 0.05, b".\r\n"]}
    )
    client = server.client()
    assert client.help() == "line one\r\n"


def test_read_article(scripted_server: Callable[..., ScriptedServer]) -> None:
    server = scripted_server({"POST": ReadArticle(b"340 send it\r\n", b"240 ok\r\n")})
    client = server.client()
    client.post({"Subject": "s"}, b"body\n")
    assert server.articles == [[b"Subject: s\r\n", b"\r\n", b"body\r\n"]]


def test_callable_and_close(scripted_server: Callable[..., ScriptedServer]) -> None:
    server = scripted_server({"DATE": lambda _line: CLOSE})
    client = server.client()
    with pytest.raises(nntp.NNTPError):
        client.date()
    client.close()


def test_greeting_and_default(scripted_server: Callable[..., ScriptedServer]) -> None:
    server = scripted_server(greeting=b"201 no posting\r\n")
    client = server.client(reader=False)
    with pytest.raises(nntp.NNTPPermanentError):
        client.date()
    client.close()
    assert server.connections == 1


def test_stop_ends_long_pause() -> None:
    """stop() must not wait for a pause in a timed reply (or leave it running)."""
    server = ScriptedServer({"HELP": [b"100 help\r\n", 60.0, b".\r\n"]})
    client = server.client(timeout=60)
    worker = threading.Thread(target=lambda: _ignore_errors(client.help))
    worker.start()
    while "HELP" not in server.received:
        time.sleep(0.01)
    started = time.monotonic()
    server.stop()
    assert time.monotonic() - started < 2
    worker.join(timeout=5)
    assert not worker.is_alive()


def _ignore_errors(call: Callable[[], object]) -> None:
    with contextlib.suppress(OSError, nntp.NNTPError):
        call()
