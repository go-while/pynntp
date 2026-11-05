"""Offline tests for commands and parsing (region C)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

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


@pytest.mark.parametrize("verb", ["NEWGROUPS", "NEWNEWS"])
@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (datetime(2026, 1, 2, 3, 4, 5), "20260102 030405 GMT"),  # noqa: DTZ001
        (
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            "20260102 030405 GMT",
        ),
        (
            datetime(
                2026, 1, 2, 1, 4, 5, tzinfo=timezone(timedelta(hours=5, minutes=30))
            ),
            "20260101 193405 GMT",
        ),
        (
            datetime(2026, 12, 31, 23, 4, 5, tzinfo=timezone(timedelta(hours=-3))),
            "20270101 020405 GMT",
        ),
    ],
)
def test_new_commands_use_gmt(
    scripted_server: Start, verb: str, timestamp: datetime, expected: str
) -> None:
    command = (
        f"NEWGROUPS {expected}"
        if verb == "NEWGROUPS"
        else f"NEWNEWS local.* {expected}"
    )
    reply = (
        b"231 groups follow\r\nlocal.test 42 7 y\r\n.\r\n"
        if verb == "NEWGROUPS"
        else b"230 articles follow\r\n<a@example.test>\r\n.\r\n"
    )
    server = scripted_server({command: reply})
    client = server.client()
    if verb == "NEWGROUPS":
        assert list(client.newgroups(timestamp)) == [
            Newsgroup("local.test", low=7, high=42, status="y")
        ]
    else:
        assert list(client.newnews("local.*", timestamp)) == ["<a@example.test>"]
    assert server.received == ["MODE READER", command]
