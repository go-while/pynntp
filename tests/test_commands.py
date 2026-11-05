"""Offline tests for commands and parsing (region C)."""

from __future__ import annotations

import binascii
import zlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

import nntp
from nntp.types import Newsgroup
from tests.scripted import ReadArticle

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

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


@pytest.mark.parametrize(
    "body",
    [
        b"good\nbad\0line\n",
        b"good\nbare\rreturn\n",
        b"bare\r",
        "good\nbad\0line",
        [b"good\n", b"bad\rline"],
    ],
)
def test_post_invalid_body_sends_nothing(
    scripted_server: Start, body: str | bytes | Iterable[bytes]
) -> None:
    server = scripted_server(
        {
            "POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n"),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="Illegal characters"):
        client.post({"Subject": "bad body"}, body)
    assert server.received == ["MODE READER"]
    assert server.articles == []
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_post_preflights_large_iterator(scripted_server: Start) -> None:
    def body() -> Iterator[bytes]:
        for _ in range(17):
            yield b"x" * 65536 + b"\n"
        yield b"bad\0line\n"

    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n")}
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError):
        client.post(body=body())
    assert server.received == ["MODE READER"]
    assert server.articles == []


def test_post_iterator_error_sends_nothing(scripted_server: Start) -> None:
    def body() -> Iterator[bytes]:
        yield b"good\n"
        raise RuntimeError("source failed")

    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n")}
    )
    client = server.client()
    with pytest.raises(RuntimeError, match="source failed"):
        client.post(body=body())
    assert server.received == ["MODE READER"]
    assert server.articles == []


def test_post_large_valid_body(scripted_server: Start) -> None:
    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n")}
    )
    line = b"x" * 65536
    assert server.client().post(body=(line for _ in range(17))) is True
    assert server.articles == [[b"\r\n", *[line + b"\r\n"] * 17]]


def test_post_header_encoding_error_sends_nothing(scripted_server: Start) -> None:
    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n")}
    )
    client = server.client()
    with pytest.raises(UnicodeEncodeError):
        client.post({"Subject": "invalid \ud800"}, b"body")
    assert server.received == ["MODE READER"]
    assert server.articles == []


@pytest.mark.parametrize("newline", ["\r", "\n", "\r\n"])
@pytest.mark.parametrize("inject_name", [False, True])
def test_post_header_injection_sends_nothing(
    scripted_server: Start, newline: str, *, inject_name: bool
) -> None:
    headers = {"Subject": "safe"}
    if inject_name:
        headers[f"X-Bad{newline}X-Injected"] = "yes"
    else:
        headers["X-Bad"] = f"safe{newline}X-Injected: yes"
    server = scripted_server(
        {
            "POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n"),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(ValueError, match="CR or LF"):
        client.post(headers, b"body")
    assert server.received == ["MODE READER"]
    assert server.articles == []
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "body",
    [
        "first\n.dot\r\n\nlast",
        b"first\n.dot\r\n\nlast",
        [b"first\n", b".dot\r\n", b"", b"last"],
        [b"first\n.dot\r\n\nlast"],
    ],
)
def test_post_normalizes_and_dot_stuffs(
    scripted_server: Start, body: str | bytes | Iterable[bytes]
) -> None:
    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 accepted\r\n")}
    )
    assert server.client().post({"Subject": "wire"}, body) is True
    assert server.articles == [
        [
            b"Subject: wire\r\n",
            b"\r\n",
            b"first\r\n",
            b"..dot\r\n",
            b"\r\n",
            b"last\r\n",
        ]
    ]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (b"Article received <id@example.test>", "<id@example.test>"),
        (b"<id@example.test> accepted", "<id@example.test>"),
        (b"Accepted (<id@example.test>)", "<id@example.test>"),
        (b"Article received", True),
        (b"", True),
    ],
)
def test_post_returns_message_id(
    scripted_server: Start, message: bytes, expected: str | bool
) -> None:
    server = scripted_server(
        {"POST": ReadArticle(b"340 send article\r\n", b"240 " + message + b"\r\n")}
    )
    assert server.client().post(body=b"ok") == expected
    assert server.received == ["MODE READER", "POST"]


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
            datetime(1, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            "00010102 030405 GMT",
        ),
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


def _yenczlib_headers(text: bytes = b"1 subject\r\n") -> bytes:
    deflate = zlib.compressobj(wbits=-15)
    compressed = deflate.compress(text) + deflate.flush()
    encoded = bytearray()
    for byte in compressed:
        byte = (byte + 42) & 0xFF
        if byte in (0, 10, 13, 61):
            encoded.extend((61, (byte + 64) & 0xFF))
        else:
            encoded.append(byte)
    if encoded.startswith(b"."):
        encoded[:0] = b"."
    return (
        b"=ybegin line=128 size=%d name=headers\r\n" % len(compressed)
        + encoded
        + b"\r\n=yend size=%d crc32=%08x\r\n.\r\n"
        % (len(compressed), binascii.crc32(compressed))
    )


@pytest.mark.parametrize("verb", ["HDR", "XHDR", "XZHDR", "XPAT"])
def test_header_command_success_codes(scripted_server: Start, verb: str) -> None:
    code = 225 if verb == "HDR" else 221
    block = _yenczlib_headers() if verb == "XZHDR" else b"1 subject\r\n.\r\n"
    server = scripted_server(
        {
            verb: f"{code} headers follow\r\n".encode() + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    if verb == "XPAT":
        assert list(client.xpat("Subject", 1, "*")) == ["1 subject"]
    else:
        values = list(getattr(client, verb.lower())("Subject", 1))
        assert [(number, value.rstrip("\r\n")) for number, value in values] == [
            (1, "subject")
        ]
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["HDR", "XHDR", "XZHDR", "XPAT"])
def test_header_command_wrong_code_drained(scripted_server: Start, verb: str) -> None:
    code = 221 if verb == "HDR" else 225
    server = scripted_server(
        {
            verb: f"{code} unexpected headers\r\n1 subject\r\n.\r\n".encode(),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    reply = (
        client.xpat("Subject", 1, "*")
        if verb == "XPAT"
        else getattr(client, verb.lower())("Subject", 1)
    )
    with pytest.raises(nntp.NNTPReplyError) as error:
        list(reply)
    assert error.value.code == code
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["HDR", "XHDR", "XZHDR"])
def test_header_values_strip_only_crlf(scripted_server: Start, verb: str) -> None:
    code = 225 if verb == "HDR" else 221
    text = b"1 subject  \t\r\n2 \r\n3\t\r\n"
    block = _yenczlib_headers(text) if verb == "XZHDR" else text + b".\r\n"
    server = scripted_server({verb: f"{code} headers\r\n".encode() + block})
    client = server.client()
    assert list(getattr(client, verb.lower())("Subject", (1, 3))) == [
        (1, "subject  \t"),
        (2, ""),
        (3, ""),
    ]


@pytest.mark.parametrize("verb", ["HDR", "XHDR", "XZHDR"])
def test_header_message_id_uses_zero(scripted_server: Start, verb: str) -> None:
    code = 225 if verb == "HDR" else 221
    key = "0" if verb == "HDR" else "<a@b>"
    text = f"{key} subject\r\n".encode()
    block = _yenczlib_headers(text) if verb == "XZHDR" else text + b".\r\n"
    server = scripted_server(
        {
            f"{verb} Subject <a@b>": f"{code} headers\r\n".encode() + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    assert list(getattr(client, verb.lower())("Subject", "<a@b>")) == [(0, "subject")]
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("verb", "selector", "key"),
    [
        ("XHDR", 1, "<a@b>"),
        ("XHDR", "<a@b>", "<other@b>"),
        ("XZHDR", 1, "<a@b>"),
        ("XZHDR", "<a@b>", "<other@b>"),
        ("HDR", "<a@b>", "<a@b>"),
        ("XHDR", 1, "not-a-number"),
        ("HDR", 1, "not-a-number"),
        ("XZHDR", 1, "not-a-number"),
    ],
)
def test_header_invalid_identifier_is_drained(
    scripted_server: Start, verb: str, selector: str | int, key: str
) -> None:
    code = 225 if verb == "HDR" else 221
    text = f"{key} subject\r\n2 remaining\r\n".encode()
    block = _yenczlib_headers(text) if verb == "XZHDR" else text + b".\r\n"
    server = scripted_server(
        {
            verb: f"{code} headers\r\n".encode() + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="Invalid"):
        list(getattr(client, verb.lower())("Subject", selector))
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
