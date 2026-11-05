from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from nntp.utils import (
    parse_date,
    parse_epoch,
    parse_headers,
    parse_newsgroup,
    unparse_headers,
    unparse_msgid_range,
    unparse_range,
)

if TYPE_CHECKING:
    from nntp.types import Newsgroup, Range


@pytest.mark.parametrize(
    ("range", "expected"),
    [
        ((1, 10), "1-10"),
        ((100,), "100-"),
        pytest.param(None, None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param((), None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param((1, 10, 20), None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_unparse_range(range: Range, expected: str) -> None:  # noqa: A002
    assert unparse_range(range) == expected


@pytest.mark.parametrize(
    ("msgid_range", "expected"),
    [
        ("msgid1", "msgid1"),
        ((1, 10), "1-10"),
        ((100,), "100-"),
        pytest.param(None, None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param((), None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param((1, 10, 20), None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_unparse_msgid_range(msgid_range: str | Range, expected: str) -> None:
    assert unparse_msgid_range(msgid_range) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("local.test 0 1 y", ("local.test", 1, 0, "y")),
        ("local.test 0 1 n", ("local.test", 1, 0, "n")),
        ("alt.test 20 10 y", ("alt.test", 10, 20, "y")),
        ("alt.test\t20\t10 ?", ("alt.test", 10, 20, "?")),
        ("alt.test 0000000042 0000000007 m\r\n", ("alt.test", 7, 42, "m")),
        pytest.param("alt.test", None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param("alt.test 10", None, marks=pytest.mark.xfail(raises=ValueError)),
        pytest.param(
            "alt.test 10 20", None, marks=pytest.mark.xfail(raises=ValueError)
        ),
    ],
)
def test_parse_newsgroup(line: str, expected: Newsgroup) -> None:
    assert parse_newsgroup(line) == expected


def test_parse_headers() -> None:
    headers = [
        "Subject: Test Subject",
        "From: John Doe <johndoe@example.com>",
        "Date: Mon, 01 Jan 2022 12:00:00 GMT",
        "Message-ID: <1234567890@example.com>",
    ]
    expected = {
        "Subject": "Test Subject",
        "FroM": "John Doe <johndoe@example.com>",
        "DATE": "Mon, 01 Jan 2022 12:00:00 GMT",
        "message-id": "<1234567890@example.com>",
    }
    assert parse_headers(headers) == expected
    assert parse_headers("\r\n".join(headers)) == expected
    assert parse_headers(StringIO("\r\n".join(headers))) == expected


def test_parse_headers_continuation() -> None:
    headers = [
        "Subject: Test Subject",
        " with continuation",
        "X-Items: Apple",
        "\tBanana",
        "\tCarrot",
    ]
    expected = {
        "Subject": "Test Subject with continuation",
        "X-Items": "Apple\tBanana\tCarrot",
    }
    assert parse_headers(headers) == expected


def test_parse_headers_invalid() -> None:
    with pytest.raises(ValueError, match="First header is a continuation"):
        parse_headers(" Subject: Test Subject")
    with pytest.raises(ValueError, match="First header is a continuation"):
        parse_headers("\twith continuation")
    with pytest.raises(ValueError, match="not enough values to unpack"):
        parse_headers("Invalid header")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("Subject\r\nX-Injected", "yes"),
        ("Subject\rX-Injected", "yes"),
        ("Subject\nX-Injected", "yes"),
        ("Subject", "safe\r\nX-Injected: yes"),
        ("Subject", "safe\rX-Injected: yes"),
        ("Subject", "safe\nX-Injected: yes"),
        ("Subject", "safe\r\n\tfolded"),
    ],
)
def test_unparse_headers_rejects_newlines(name: str, value: str) -> None:
    with pytest.raises(ValueError, match="CR or LF"):
        unparse_headers({"X-Safe": "first", name: value})


def test_unparse_headers_valid() -> None:
    assert unparse_headers({}) == "\r\n"
    assert unparse_headers({"Subject": "café:  text\tvalue", "X-Empty": ""}) == (
        "Subject: café:  text\tvalue\r\nX-Empty: \r\n\r\n"
    )


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("20220101144001", datetime(2022, 1, 1, 14, 40, 1, tzinfo=timezone.utc)),
        (20220101144001, datetime(2022, 1, 1, 14, 40, 1, tzinfo=timezone.utc)),
        pytest.param("2022", None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_parse_date(date: str | int, expected: datetime) -> None:
    assert parse_date(date) == expected


@pytest.mark.parametrize(
    ("epoch", "expected"),
    [
        ("1641048001", datetime(2022, 1, 1, 14, 40, 1, tzinfo=timezone.utc)),
        (1641048001, datetime(2022, 1, 1, 14, 40, 1, tzinfo=timezone.utc)),
    ],
)
def test_parse_epoch(epoch: str | int, expected: datetime) -> None:
    assert parse_epoch(epoch) == expected
