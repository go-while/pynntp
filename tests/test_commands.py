"""Offline tests for commands and parsing (region C)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from nntp.types import Newsgroup

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.scripted import ScriptedServer

    Start = Callable[..., ScriptedServer]


def test_list_active_water_marks(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST ACTIVE local.*": (
                b"215 list follows\r\n"
                b"local.test 0000000042 0000000007 y\r\n"
                b"local.empty 0000000000 0000000001 n\r\n.\r\n"
            ),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    assert list(client.list_active("local.*")) == [
        Newsgroup("local.test", low=7, high=42, status="y"),
        Newsgroup("local.empty", low=1, high=0, status="n"),
    ]
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert server.received == ["MODE READER", "LIST ACTIVE local.*", "DATE"]


def test_newgroups_water_marks(scripted_server: Start) -> None:
    server = scripted_server(
        {"NEWGROUPS": b"231 groups follow\r\nlocal.test 42 7 m\r\n.\r\n"}
    )
    client = server.client()
    groups = list(client.newgroups(datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert groups == [Newsgroup("local.test", low=7, high=42, status="m")]
