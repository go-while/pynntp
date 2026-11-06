"""Offline tests for commands and parsing (region C)."""

from __future__ import annotations

import binascii
import gzip
import io
import tempfile
import zlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest import mock

import pytest

import nntp
from nntp.types import Newsgroup
from tests.scripted import ReadArticle, StartCompression

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from nntp.types import Range
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

    def call() -> Iterator[object]:
        return (
            client.xpat("Subject", 1, "*")
            if verb == "XPAT"
            else getattr(client, verb.lower())("Subject", 1)
        )

    with pytest.raises(nntp.NNTPReplyError) as error:
        call()
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


@pytest.mark.parametrize("verb", ["XOVER", "XZVER"])
@pytest.mark.parametrize("suffix", ["full", "FULL", "FuLl"])
def test_overview_full_fields_and_empty_values(
    scripted_server: Start, verb: str, suffix: str
) -> None:
    text = (
        b"1\tsubject\tXrEf: host local.test:1  \r\n2\tsecond\t\r\n3\tthird\tXref:\r\n"
    )
    block = _yenczlib_headers(text) if verb == "XZVER" else text + b".\r\n"
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": (
                f"215 format\r\nSubject:\r\nXref:{suffix}\r\n.\r\n".encode()
            ),
            verb: b"224 overview\r\n" + block,
        }
    )
    client = server.client()
    assert client.overview_fmt == ("Subject", "Xref")
    entries = list(getattr(client, verb.lower())((1, 3)))
    assert [(number, fields["Xref"]) for number, fields in entries] == [
        (1, "host local.test:1  "),
        (2, ""),
        (3, ""),
    ]
    assert entries[0][1]["Subject"] == "subject"
    assert server.received.count("LIST OVERVIEW.FMT") == 1


@pytest.mark.parametrize("value", ["Other: host", "missing-label"])
@pytest.mark.parametrize("verb", ["XOVER", "XZVER"])
def test_overview_nonconforming_full_field_is_preserved(
    scripted_server: Start, value: str, verb: str
) -> None:
    text = f"1\t{value}\r\n2\tXref: host\r\n".encode()
    block = _yenczlib_headers(text) if verb == "XZVER" else text + b".\r\n"
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": b"215 format\r\nXref:full\r\n.\r\n",
            verb: b"224 overview\r\n" + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    entries = list(getattr(client, verb.lower())((1, 2)))
    assert [(number, fields["Xref"]) for number, fields in entries] == [
        (1, value),
        (2, "host"),
    ]
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_overview_manual_format_does_not_request_metadata(
    scripted_server: Start,
) -> None:
    server = scripted_server({"XOVER": b"224 overview\r\n1\tsubject\r\n.\r\n"})
    client = server.client()
    client.overview_fmt = ("Subject",)
    entries = list(client.xover(1))
    assert entries[0][1]["Subject"] == "subject"
    assert server.received == ["MODE READER", "XOVER 1"]


def test_overview_format_fallback(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": b"500 unknown\r\n",
            "XOVER": b"224 overview\r\n1\tsubject\tfrom\tdate\t<a@b>\t\t10\t1\r\n.\r\n",
        }
    )
    client = server.client()
    entries = list(client.xover(1))
    assert entries[0][1]["Subject"] == "subject"
    assert entries[0][1]["References"] == ""
    assert entries[0][1]["Lines"] == "1"


@pytest.mark.parametrize(
    "timestamp", ["not-a-date", "20261301000000", "20260101000060"]
)
def test_invalid_date_raises_data_error(scripted_server: Start, timestamp: str) -> None:
    replies = iter([f"111 {timestamp}\r\n".encode(), b"111 20260102030405\r\n"])
    server = scripted_server({"DATE": lambda _line: next(replies)})
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="DATE"):
        client.date()
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["LIST ACTIVE", "NEWGROUPS"])
@pytest.mark.parametrize("line", [b"missing-fields", b"local.test NaN 1 y"])
def test_invalid_newsgroup_raises_data_error(
    scripted_server: Start, verb: str, line: bytes
) -> None:
    code = 215 if verb == "LIST ACTIVE" else 231
    server = scripted_server(
        {
            verb: f"{code} groups\r\n".encode() + line + b"\r\nlocal.ok 2 1 y\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    groups = (
        client.list_active()
        if verb == "LIST ACTIVE"
        else client.newgroups(datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    with pytest.raises(nntp.NNTPDataError, match="newsgroup"):
        list(groups)
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_list_extensions_legacy_success(scripted_server: Start) -> None:
    server = scripted_server(
        {"LIST EXTENSIONS": b"202 extensions\r\nHDR\r\nOVER\r\n.\r\n"}
    )
    assert list(server.client().list_extensions()) == ["HDR", "OVER"]


def test_list_extensions_unsupported_propagates(scripted_server: Start) -> None:
    server = scripted_server(
        {"LIST EXTENSIONS": b"501 not supported\r\n", "DATE": b"111 20260102030405\r\n"}
    )
    client = server.client()
    with pytest.raises(nntp.NNTPPermanentError) as error:
        list(client.list_extensions())
    assert error.value.code == 501
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("selector", "command", "number"),
    [(None, "STAT", 42), (42, "STAT 42", 42), ("<a@b>", "STAT <a@b>", 0)],
)
def test_stat_forms(
    scripted_server: Start, selector: str | int | None, command: str, number: int
) -> None:
    server = scripted_server(
        {command: f"223 {number} <a@b> article exists\r\n".encode()}
    )
    assert server.client().stat(selector) == (number, "<a@b>")
    assert server.received == ["MODE READER", command]


@pytest.mark.parametrize(
    "message", [b"no-number <a@b>", b"1", b"1 no-id", b"-1 <a@b>", b"1 <>"]
)
def test_stat_invalid_data(scripted_server: Start, message: bytes) -> None:
    server = scripted_server(
        {"STAT": b"223 " + message + b"\r\n", "DATE": b"111 20260102030405\r\n"}
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="STAT"):
        client.stat()
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("name", "article_range", "command", "numbers"),
    [
        (None, None, "LISTGROUP", [1, 3, 7]),
        ("local.test", None, "LISTGROUP local.test", [1, 3, 7]),
        ("local.test", 1, "LISTGROUP local.test 1", [1]),
        ("local.test", (1,), "LISTGROUP local.test 1-", [1, 3, 7]),
        ("local.test", (1, 3), "LISTGROUP local.test 1-3", [1, 3]),
    ],
)
def test_listgroup_forms(
    scripted_server: Start,
    name: str | None,
    article_range: Range | None,
    command: str,
    numbers: list[int],
) -> None:
    block = b"".join(f"{number}\r\n".encode() for number in numbers)
    server = scripted_server(
        {command: b"211 3 1 7 local.test list follows\r\n" + block + b".\r\n"}
    )
    assert list(server.client().listgroup(name, article_range)) == numbers
    assert server.received == ["MODE READER", command]


def test_listgroup_empty_and_range_requires_name(scripted_server: Start) -> None:
    server = scripted_server({"LISTGROUP": b"211 0 0 0 local.empty\r\n.\r\n"})
    client = server.client()
    with pytest.raises(ValueError, match="name"):
        list(client.listgroup(range=(1, 3)))
    assert server.received == ["MODE READER"]
    assert list(client.listgroup("local.empty")) == []


@pytest.mark.parametrize("status", ["bad", "3 NaN 7 local.test", "-1 1 7 local.test"])
def test_listgroup_bad_status_drains(scripted_server: Start, status: str) -> None:
    server = scripted_server(
        {
            "LISTGROUP": f"211 {status}\r\n1\r\n3\r\n.\r\n".encode(),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="LISTGROUP"):
        list(client.listgroup())
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("number", ["0", "-1", "NaN"])
def test_listgroup_bad_number_drains(scripted_server: Start, number: str) -> None:
    server = scripted_server(
        {
            "LISTGROUP": f"211 3 1 7 local.test\r\n{number}\r\n3\r\n.\r\n".encode(),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="LISTGROUP"):
        list(client.listgroup())
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_listgroup_abandoned_reply_drains(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LISTGROUP": b"211 3 1 7 local.test\r\n1\r\n3\r\n7\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    assert next(client.listgroup("local.test")) == 1
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("selector", "args", "number"),
    [
        (None, "", 1),
        (1, " 1", 1),
        ((1,), " 1-", 1),
        ((1, 3), " 1-3", 1),
        ("<a@b>", " <a@b>", 0),
        ("<a@b>", " <a@b>", 7),
    ],
)
def test_over_forms(
    scripted_server: Start, selector: str | Range | None, args: str, number: int
) -> None:
    reply = (
        f"224 overview\r\n{number}\tsubject\tXref: host local.test:1\r\n.\r\n".encode()
    )
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": b"215 format\r\nSubject:\r\nXref:FULL\r\n.\r\n",
            f"OVER{args}": reply,
        }
    )
    entries = list(server.client().over(selector))
    assert [(n, fields["Subject"], fields["Xref"]) for n, fields in entries] == [
        (number, "subject", "host local.test:1")
    ]
    assert server.received == ["MODE READER", "LIST OVERVIEW.FMT", f"OVER{args}"]


@pytest.mark.parametrize("verb", ["STAT", "LISTGROUP", "OVER"])
def test_new_command_wrong_success_drains(scripted_server: Start, verb: str) -> None:
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": b"500 unknown\r\n",
            verb: b"215 wrong success\r\nignored\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()

    def run_command() -> None:
        result = getattr(client, verb.lower())()
        if verb != "STAT":
            list(result)

    with pytest.raises(nntp.NNTPReplyError) as error:
        run_command()
    assert error.value.code == 215
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_over_message_id_unsupported(scripted_server: Start) -> None:
    server = scripted_server(
        {"LIST OVERVIEW.FMT": b"500 unknown\r\n", "OVER": b"503 MSGID unsupported\r\n"}
    )
    with pytest.raises(nntp.NNTPPermanentError) as error:
        list(server.client().over("<a@b>"))
    assert error.value.code == 503


@pytest.mark.parametrize(
    ("verb", "code"), [("STAT", 430), ("LISTGROUP", 411), ("OVER", 423)]
)
def test_new_command_negative_response_is_reusable(
    scripted_server: Start, verb: str, code: int
) -> None:
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": b"500 unknown\r\n",
            verb: f"{code} no article or group\r\n".encode(),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()

    def run_command() -> None:
        result = getattr(client, verb.lower())()
        if verb != "STAT":
            list(result)

    with pytest.raises(nntp.NNTPTemporaryError) as error:
        run_command()
    assert error.value.code == code
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("method", "command", "args"),
    [
        ("date", "DATE", ()),
        ("help", "HELP", ()),
        ("newgroups", "NEWGROUPS", (datetime(2026, 1, 1, tzinfo=timezone.utc),)),
        ("newnews", "NEWNEWS", ("local.*", datetime(2026, 1, 1, tzinfo=timezone.utc))),
        ("list", "LIST", ()),
        ("list_active", "LIST ACTIVE", ()),
        ("list_active_times", "LIST ACTIVE.TIMES", ()),
        ("list_headers", "LIST HEADERS", ()),
        ("list_newsgroups", "LIST NEWSGROUPS", ()),
        ("list_overview_fmt", "LIST OVERVIEW.FMT", ()),
        ("list_extensions", "LIST EXTENSIONS", ()),
        ("group", "GROUP", ("local.test",)),
        ("next", "NEXT", ()),
        ("last", "LAST", ()),
        ("hdr", "HDR", ("Subject", 1)),
        ("xhdr", "XHDR", ("Subject", 1)),
        ("xzhdr", "XZHDR", ("Subject", 1)),
        ("xpat", "XPAT", ("Subject", 1, "*")),
        ("xover", "XOVER", (1,)),
        ("xzver", "XZVER", (1,)),
        ("xfeature_compress_gzip", "XFEATURE COMPRESS GZIP", ()),
        ("post", "POST", ()),
        ("post_final", "POST", ()),
    ],
)
def test_command_unexpected_multiline_success_is_drained(
    scripted_server: Start, method: str, command: str, args: tuple[object, ...]
) -> None:
    code = 101 if method == "help" else 100
    wrong = f"{code} unexpected\r\nignored\r\n.\r\n".encode()
    server = scripted_server(
        {
            command: ReadArticle(b"340 send article\r\n", wrong)
            if method == "post_final"
            else wrong,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    if method == "date":
        replies = iter([wrong, b"111 20260102030405\r\n"])
        server.script["DATE"] = lambda _line: next(replies)
    client = server.client()
    if method in ("xover", "xzver"):
        client.overview_fmt = ("Subject",)
    eager = {
        "date",
        "help",
        "group",
        "next",
        "last",
        "xfeature_compress_gzip",
        "post",
        "post_final",
    }

    def run_command() -> None:
        name = "post" if method == "post_final" else method
        result = getattr(client, name)(*args)
        if method not in eager:
            list(result)

    with pytest.raises(nntp.NNTPReplyError) as error:
        run_command()
    assert error.value.code == code
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_unexpected_compressed_success_is_drained(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "HELP": b"215 [COMPRESS=GZIP]\r\n" + gzip.compress(b"ignored\r\n.\r\n"),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPReplyError) as error:
        client.help()
    assert error.value.code == 215
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_unexpected_singleline_success_does_not_drain(scripted_server: Start) -> None:
    server = scripted_server(
        {"HELP": b"200 unexpected\r\n", "DATE": b"111 20260102030405\r\n"}
    )
    client = server.client()
    with pytest.raises(nntp.NNTPReplyError) as error:
        client.help()
    assert error.value.code == 200
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "body",
    [
        "first\n.dot\r\n\nlast",
        b"first\n.dot\r\n\nlast",
        [b"first", b".dot\n", b"", b"last"],
    ],
)
def test_ihave_transfers_prepared_article(
    scripted_server: Start, body: str | bytes | Iterable[bytes]
) -> None:
    server = scripted_server(
        {
            "IHAVE <a@b>": ReadArticle(b"335 send article\r\n", b"235 transferred\r\n"),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    assert client.ihave("<a@b>", {"Message-ID": "<a@b>"}, body) is True
    assert server.articles == [
        [
            b"Message-ID: <a@b>\r\n",
            b"\r\n",
            b"first\r\n",
            b"..dot\r\n",
            b"\r\n",
            b"last\r\n",
        ]
    ]
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert server.received == ["IHAVE <a@b>", "DATE"]


@pytest.mark.parametrize(
    ("code", "final"), [(435, False), (436, False), (436, True), (437, True)]
)
def test_ihave_rejection_is_reusable(
    scripted_server: Start, code: int, *, final: bool
) -> None:
    rejection = f"{code} refused\r\n".encode()
    server = scripted_server(
        {
            "IHAVE": ReadArticle(b"335 send article\r\n", rejection)
            if final
            else rejection,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    with pytest.raises(nntp.NNTPTemporaryError) as error:
        client.ihave("<a@b>", body=b"article")
    assert error.value.code == code
    assert server.articles == ([[b"\r\n", b"article\r\n"]] if final else [])
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("final", [False, True])
def test_ihave_unexpected_multiline_is_drained(
    scripted_server: Start, *, final: bool
) -> None:
    wrong = b"100 wrong success\r\nignored\r\n.\r\n"
    server = scripted_server(
        {
            "IHAVE": ReadArticle(b"335 send article\r\n", wrong) if final else wrong,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    with pytest.raises(nntp.NNTPReplyError) as error:
        client.ihave("<a@b>")
    assert error.value.code == 100
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "message_id",
    [
        "",
        "<>",
        "a@b",
        "<a b>",
        "<a\r\nb>",
        "<a\0b>",
        "<<a@b>>",
        "<café@b>",
        "<" + "a" * 249 + ">",
    ],
)
def test_ihave_invalid_id_sends_nothing(
    scripted_server: Start, message_id: str
) -> None:
    server = scripted_server()
    client = server.client(reader=False)
    with pytest.raises(ValueError, match="Message-ID"):
        client.ihave(message_id)
    assert server.received == []
    assert server.articles == []


@pytest.mark.parametrize(
    "body", [b"good\nbad\0", b"good\nbad\r", [b"good", b"bad\rline"]]
)
def test_ihave_invalid_body_sends_nothing(
    scripted_server: Start, body: bytes | Iterable[bytes]
) -> None:
    server = scripted_server()
    client = server.client(reader=False)
    with pytest.raises(nntp.NNTPDataError, match="Illegal characters"):
        client.ihave("<a@b>", body=body)
    assert server.received == []
    assert server.articles == []


def test_ihave_header_injection_sends_nothing(scripted_server: Start) -> None:
    server = scripted_server()
    client = server.client(reader=False)
    with pytest.raises(ValueError, match="CR or LF"):
        client.ihave("<a@b>", {"Subject": "safe\r\nX-Injected: yes"})
    assert server.received == []


def test_ihave_preflights_large_failing_source(scripted_server: Start) -> None:
    server = scripted_server()
    client = server.client(reader=False)

    def source() -> Iterator[bytes]:
        for _ in range(17):
            yield b"x" * 65536 + b"\n"
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError, match="source failed"):
        client.ihave("<a@b>", body=source())
    assert server.received == []
    assert server.articles == []


def test_ihave_large_body_and_optional_headers(scripted_server: Start) -> None:
    server = scripted_server({"IHAVE": ReadArticle(b"335 send\r\n", b"235 ok\r\n")})
    line = b"x" * 65536
    assert (
        server.client(reader=False).ihave("<a@b>", body=(line for _ in range(17)))
        is True
    )
    assert server.articles == [[b"\r\n", *[line + b"\r\n"] * 17]]


@pytest.mark.parametrize(("code", "final"), [(235, False), (240, True)])
def test_ihave_rejects_other_success_codes(
    scripted_server: Start, code: int, *, final: bool
) -> None:
    wrong = f"{code} not the expected success\r\n".encode()
    server = scripted_server(
        {
            "IHAVE": ReadArticle(b"335 send\r\n", wrong) if final else wrong,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    with pytest.raises(nntp.NNTPReplyError) as error:
        client.ihave("<a@b>")
    assert error.value.code == code
    assert bool(server.articles) == final
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_ihave_does_not_pipeline_while_reply_held(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST": b"215 list\r\nlocal.test 1 1 y\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    reply = client.list()
    with pytest.raises(nntp.nntp.NNTPSyncError):  # public export is part of B6
        client.ihave("<a@b>", body=b"article")
    assert server.received == ["LIST"]
    del reply
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_ihave_preflights_before_offer_and_keeps_header_id(
    scripted_server: Start,
) -> None:
    offered_id = "<" + "a" * 248 + ">"  # RFC 3977's 250-character limit.
    prepared = False

    def source() -> Iterator[bytes]:
        nonlocal prepared
        yield b"body\n"
        prepared = True

    def accept(_command: str) -> ReadArticle:
        assert prepared
        return ReadArticle(b"335 send\r\n", b"235\r\n")

    server = scripted_server({f"IHAVE {offered_id}": accept})
    assert (
        server.client(reader=False).ihave(
            offered_id, {"Message-ID": "<different@b>"}, source()
        )
        is True
    )
    assert server.articles == [[b"Message-ID: <different@b>\r\n", b"\r\n", b"body\r\n"]]


EAGER_COMMANDS = [
    (
        "newgroups",
        "NEWGROUPS",
        (datetime(2026, 1, 1, tzinfo=timezone.utc),),
        231,
        b"local.test 2 1 y\r\n",
    ),
    (
        "newnews",
        "NEWNEWS",
        ("local.*", datetime(2026, 1, 1, tzinfo=timezone.utc)),
        230,
        b"<a@b>\r\n",
    ),
    ("list", "LIST", (), 215, b"local.test 2 1 y\r\n"),
    ("list_active", "LIST ACTIVE", (), 215, b"local.test 2 1 y\r\n"),
    ("list_active_times", "LIST ACTIVE.TIMES", (), 215, b"local.test 123 tester\r\n"),
    ("list_headers", "LIST HEADERS", (), 215, b"Subject\r\n"),
    ("list_newsgroups", "LIST NEWSGROUPS", (), 215, b"local.test description\r\n"),
    ("list_overview_fmt", "LIST OVERVIEW.FMT", (), 215, b"Subject:\r\n"),
    ("list_extensions", "LIST EXTENSIONS", (), 202, b"OVER\r\n"),
    ("listgroup", "LISTGROUP", (), 211, b"1\r\n"),
    ("hdr", "HDR", ("Subject",), 225, b"1 subject\r\n"),
    ("xhdr", "XHDR", ("Subject",), 221, b"1 subject\r\n"),
    ("xzhdr", "XZHDR", ("Subject",), 221, b"1 subject\r\n"),
    ("over", "OVER", (), 224, b"1\tsubject\r\n"),
    ("xover", "XOVER", (), 224, b"1\tsubject\r\n"),
    ("xzver", "XZVER", (), 224, b"1\tsubject\r\n"),
    ("xpat", "XPAT", ("Subject", 1, "*"), 221, b"1 subject\r\n"),
]


@pytest.mark.parametrize(("method", "command", "args", "code", "text"), EAGER_COMMANDS)
@pytest.mark.parametrize("action", ["consume", "drop", "close"])
def test_iterator_commands_send_at_call_and_own_reply(
    scripted_server: Start,
    method: str,
    command: str,
    args: tuple[object, ...],
    code: int,
    text: bytes,
    action: str,
) -> None:
    metadata = "1 1 1 local.test" if method == "listgroup" else "reply"
    block = _yenczlib_headers(text) if method in ("xzhdr", "xzver") else text + b".\r\n"
    server = scripted_server(
        {
            command: f"{code} {metadata}\r\n".encode() + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    client.overview_fmt = ("Subject",)
    reply = getattr(client, method)(*args)
    assert len(server.received) == 1
    assert server.received[0].startswith(command)
    with pytest.raises(nntp.nntp.NNTPSyncError):
        client.date()
    if action == "consume":
        assert len(list(reply)) == 1
    elif action == "close":
        reply.close()  # An unstarted parsing wrapper must release its source.
    else:
        del reply
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("method", "command", "args", "_code", "_text"), EAGER_COMMANDS
)
def test_iterator_command_errors_raise_at_call(
    scripted_server: Start,
    method: str,
    command: str,
    args: tuple[object, ...],
    _code: int,
    _text: bytes,
) -> None:
    server = scripted_server({command: b"500 unavailable\r\n"})
    client = server.client(reader=False)
    client.overview_fmt = ("Subject",)
    with pytest.raises(nntp.NNTPPermanentError, match="500"):
        getattr(client, method)(*args)


def test_eager_parser_error_releases_reply_with_live_traceback(
    scripted_server: Start,
) -> None:
    server = scripted_server(
        {
            "LIST ACTIVE": b"215 list\r\nmalformed\r\nlocal.test 2 1 y\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    reply = client.list_active()
    with pytest.raises(nntp.NNTPDataError) as error:
        next(reply)
    assert error.value.__traceback__ is not None
    # Hold both the failed iterator and its exception, including traceback.
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_eager_started_iterator_close_releases_source(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST ACTIVE": b"215 list\r\nlocal.one 2 1 y\r\nlocal.two 3 1 y\r\n.\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    reply = client.list_active()
    assert next(reply).name == "local.one"
    assert hasattr(reply, "close")
    reply.close()
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(("method", "command", "args", "code", "_text"), EAGER_COMMANDS)
def test_eager_empty_reply_is_streamed(
    scripted_server: Start,
    method: str,
    command: str,
    args: tuple[object, ...],
    code: int,
    _text: bytes,
) -> None:
    metadata = "0 0 0 local.empty" if method == "listgroup" else "empty"
    block = _yenczlib_headers(b"") if method in ("xzhdr", "xzver") else b".\r\n"
    server = scripted_server(
        {
            command: f"{code} {metadata}\r\n".encode() + block,
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    client.overview_fmt = ("Subject",)
    reply = getattr(client, method)(*args)
    assert len(server.received) == 1
    assert list(reply) == []
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_eager_command_does_not_read_reply_data_at_call(scripted_server: Start) -> None:
    server = scripted_server(
        {"LIST ACTIVE": [b"215 list\r\n", 60.0, b"local.test 2 1 y\r\n.\r\n"]}
    )
    client = server.client(reader=False, timeout=0.1)
    reply = client.list_active()  # Reading even one data line here would time out.
    assert server.received == ["LIST ACTIVE"]
    client.close()
    del reply


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("timeout_at", [1, 2])
@pytest.mark.parametrize("close_fails", [False, True])
def test_article_partial_send_timeout_closes_without_retry(
    scripted_server: Start,
    monkeypatch: pytest.MonkeyPatch,
    verb: str,
    timeout_at: int,
    *,
    close_fails: bool,
) -> None:
    ready, accepted = (340, 240) if verb == "POST" else (335, 235)
    server = scripted_server(
        {
            verb: ReadArticle(
                f"{ready} send article\r\n".encode(), f"{accepted} ok\r\n".encode()
            )
        }
    )
    client = server.client(reader=False)
    real_socket = client.socket
    body_sends = 0

    def send(data: bytes) -> None:
        nonlocal body_sends
        if data.startswith((b"POST\r\n", b"IHAVE ")):
            real_socket.sendall(data)
            return
        body_sends += 1
        if body_sends == timeout_at:
            real_socket.sendall(data[:7])  # Some bytes reached the server.
            raise TimeoutError("partial article send timed out")
        real_socket.sendall(data)

    def failing_close() -> None:
        real_socket.close()
        raise OSError("close failed")

    if close_fails:
        monkeypatch.setattr(client, "close", failing_close)
    fake = mock.Mock(wraps=real_socket)
    fake.sendall.side_effect = send
    client.socket = fake
    args = ("<a@b>",) if verb == "IHAVE" else ()
    try:
        with pytest.raises(nntp.NNTPTimeoutError) as error:
            getattr(client, verb.lower())(*args, body=[b"x" * 65536] * 3)
        assert isinstance(error.value, TimeoutError)
        assert isinstance(error.value.__cause__, TimeoutError)
        assert real_socket.fileno() == -1
        assert body_sends == timeout_at
        assert server.received == (["POST"] if verb == "POST" else ["IHAVE <a@b>"])
        with pytest.raises(nntp.NNTPError, match="closed"):
            client.date()
    finally:
        client.socket = real_socket  # Fixture teardown closes the actual socket.


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("final", [False, True])
def test_article_status_timeout_closes_without_retry(
    scripted_server: Start, verb: str, *, final: bool
) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server(
        {
            verb: ReadArticle(f"{ready} send\r\n".encode(), b"")
            if final
            else [60.0, b"335 late\r\n"]
        }
    )
    client = server.client(reader=False)
    client.socket.settimeout(0.05)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPTimeoutError):
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert client.socket.fileno() == -1
    assert len(server.received) == 1
    assert bool(server.articles) == final
    with pytest.raises(nntp.NNTPError, match="closed"):
        client.date()


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_article_source_timeout_does_not_close_or_send(
    scripted_server: Start, verb: str
) -> None:
    server = scripted_server({"DATE": b"111 20260102030405\r\n"})
    client = server.client(reader=False)

    def source() -> Iterator[bytes]:
        yield b"good\n"
        raise TimeoutError("source timed out before transfer")

    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(TimeoutError, match="source") as error:
        getattr(client, verb.lower())(*args, body=source())
    assert not isinstance(error.value, nntp.NNTPError)
    assert client.socket.fileno() != -1
    assert server.received == []
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("final", [False, True])
def test_article_preserves_typed_status_timeout_and_cause(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, verb: str, *, final: bool
) -> None:
    ready, accepted = (340, 240) if verb == "POST" else (335, 235)
    server = scripted_server(
        {verb: ReadArticle(f"{ready} send\r\n".encode(), f"{accepted} ok\r\n".encode())}
    )
    client = server.client(reader=False)
    real_status = client.status
    original = nntp.NNTPTimeoutError("transport timed out")
    cause = TimeoutError("underlying read timeout")
    original.__cause__ = cause
    statuses = 0

    def status() -> tuple[int, str]:
        nonlocal statuses
        statuses += 1
        if statuses == (2 if final else 1):
            raise original
        return real_status()

    monkeypatch.setattr(client, "status", status)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPTimeoutError) as error:
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert error.value is original
    assert error.value.__cause__ is cause
    assert client.socket.fileno() == -1


def test_list_newsgroups_can_omit_undescribed_active_group(
    scripted_server: Start,
) -> None:
    """Issue #95 is server metadata, not a client cache or a missing group."""
    server = scripted_server(
        {
            "LIST NEWSGROUPS local.*": (
                b"215 descriptions\r\n"
                b"local.described A group with a description.\r\n.\r\n"
            ),
            "LIST ACTIVE local.*": (
                b"215 groups\r\nlocal.described 2 1 y\r\nlocal.new 0 1 y\r\n.\r\n"
            ),
        }
    )
    client = server.client()
    assert list(client.list_newsgroups("local.*")) == [
        ("local.described", "A group with a description.")
    ]
    assert {group.name for group in client.list_active("local.*")} == {
        "local.described",
        "local.new",
    }
    server.script["LIST NEWSGROUPS local.*"] = (
        b"215 descriptions\r\nlocal.described A group with a description.\r\n"
        b"local.new Newly added description.\r\n.\r\n"
    )
    assert list(client.list_newsgroups("local.*"))[-1] == (
        "local.new",
        "Newly added description.",
    )


def _compress_article_connection(client: nntp.NNTPClient) -> None:
    """Use I6 directly until B9's public compress() command is available."""
    assert client.command("COMPRESS DEFLATE")[0] == 206
    client._start_compression()  # noqa: SLF001


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("kind", ["text", "bytes", "lines", "spooled"])
def test_compressed_article_transfer(
    scripted_server: Start, verb: str, kind: str
) -> None:
    ready, accepted = (340, 240) if verb == "POST" else (335, 235)
    message_id = "<compressed@example.test>"
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            verb: ReadArticle(
                f"{ready} send\r\n".encode(),
                f"{accepted} accepted {message_id}\r\n".encode(),
            ),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False, timeout=1)
    _compress_article_connection(client)
    # Two articles share the same compressor/dictionary, including the command
    # between them. The large iterable spills to disk and crosses send chunks.
    for _ in range(2):
        body: str | bytes | Iterable[bytes]
        if kind == "spooled":
            line = b"." + b"x" * 65535
            body = (line for _ in range(17))
            wire_body = (b"." + line + b"\r\n") * 17
        else:
            text = "first\n.dot\r\n.\n\nlast\n"
            body = text if kind == "text" else text.encode()
            if kind == "lines":
                body = iter([b"first", b".dot\r\n", b".\n", b"", b"last\n"])
            wire_body = b"first\r\n..dot\r\n..\r\n\r\nlast\r\n"
        args = (message_id,) if verb == "IHAVE" else ()
        result = getattr(client, verb.lower())(*args, {"Subject": "compressed"}, body)
        assert result == (message_id if verb == "POST" else True)
        assert (
            b"".join(server.articles[-1]) == b"Subject: compressed\r\n\r\n" + wire_body
        )
        assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert len(server.articles) == 2
    assert client.compressed


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("final", [False, True])
def test_compressed_article_refusal_is_reusable(
    scripted_server: Start, verb: str, *, final: bool
) -> None:
    ready, refused = (340, 441) if verb == "POST" else (335, 437)
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            verb: ReadArticle(
                f"{ready} send\r\n".encode(), f"{refused} refused\r\n".encode()
            )
            if final
            else b"440 not wanted\r\n",
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False, timeout=1)
    _compress_article_connection(client)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPTemporaryError):
        getattr(client, verb.lower())(*args, body=b".body\n")
    assert bool(server.articles) == final
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("failure", ["header", "body", "source"])
def test_compressed_article_preflight_sends_nothing(
    scripted_server: Start, verb: str, failure: str
) -> None:
    server = scripted_server(
        {"COMPRESS DEFLATE": StartCompression(), "DATE": b"111 20260102030405\r\n"}
    )
    client = server.client(reader=False)
    _compress_article_connection(client)

    def source() -> Iterator[bytes]:
        yield b"valid\n"
        raise TimeoutError("caller source timed out")

    headers = {"Subject": "bad\r\nheader"} if failure == "header" else None
    body = source() if failure == "source" else b"valid\nbad\0"
    expected = {
        "header": ValueError,
        "body": nntp.NNTPDataError,
        "source": TimeoutError,
    }
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(expected[failure]) as error:
        getattr(client, verb.lower())(*args, headers=headers, body=body)
    if failure == "source":
        assert not isinstance(error.value, nntp.NNTPError)
    assert server.received == ["COMPRESS DEFLATE"]
    assert server.articles == []
    assert client.date() == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_compressed_article_partial_send_timeout_closes(
    scripted_server: Start, verb: str
) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            verb: ReadArticle(f"{ready} send\r\n".encode(), b""),
        }
    )
    client = server.client(reader=False, timeout=1)
    _compress_article_connection(client)
    real_socket = client.socket
    writes = 0

    def send(data: bytes) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:  # First article write, after the compressed command.
            real_socket.sendall(data[:1])
            raise TimeoutError("partial compressed article")
        real_socket.sendall(data)

    fake = mock.Mock(wraps=real_socket)
    fake.sendall.side_effect = send
    client.socket = fake
    args = ("<a@b>",) if verb == "IHAVE" else ()
    try:
        with pytest.raises(nntp.NNTPTimeoutError) as error:
            getattr(client, verb.lower())(*args, body=b".body\n")
        assert isinstance(error.value.__cause__, TimeoutError)
        assert real_socket.fileno() == -1
        assert writes == 2  # No retry of either command or article.
        with pytest.raises(nntp.NNTPError, match="closed"):
            client.date()
    finally:
        client.socket = real_socket


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_compressed_article_final_status_timeout_closes(
    scripted_server: Start, verb: str
) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            verb: ReadArticle(f"{ready} send\r\n".encode(), b""),
        }
    )
    client = server.client(reader=False)
    _compress_article_connection(client)
    client.socket.settimeout(0.05)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPTimeoutError):
        getattr(client, verb.lower())(*args, body=b".body\n")
    # The whole article arrived, but its acknowledgement was lost. Retrying
    # could duplicate it, so close without issuing any further wire command.
    assert server.articles == [[b"\r\n", b"..body\r\n"]]
    assert client.socket.fileno() == -1
    with pytest.raises(nntp.NNTPError, match="closed"):
        client.date()
    assert server.received == [
        "COMPRESS DEFLATE",
        "POST" if verb == "POST" else "IHAVE <a@b>",
    ]


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
@pytest.mark.parametrize("phase", ["write", "spool", "status"])
@pytest.mark.parametrize("fault_type", [OSError, RuntimeError, KeyboardInterrupt])
@pytest.mark.parametrize("compressed", [False, True])
def test_article_non_timeout_failure_closes_uncertain_transfer(
    scripted_server: Start,
    monkeypatch: pytest.MonkeyPatch,
    verb: str,
    phase: str,
    fault_type: type[BaseException],
    *,
    compressed: bool,
) -> None:
    ready, accepted = (340, 240) if verb == "POST" else (335, 235)
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            verb: ReadArticle(
                f"{ready} send\r\n".encode(), f"{accepted} ok\r\n".encode()
            ),
        }
    )
    client = server.client(reader=False)
    if compressed:
        _compress_article_connection(client)
    fault = fault_type("article transfer interrupted")
    real_send = client._sendall  # noqa: SLF001 (exercise the C transport hook)
    real_status = client.status

    if phase == "write":

        def send(data: bytes) -> None:
            if data.startswith((b"POST\r\n", b"IHAVE ")):
                real_send(data)
            else:
                real_send(data[:5])
                raise fault

        monkeypatch.setattr(client, "_sendall", send)
    elif phase == "spool":

        class UnreadableArticle(io.BytesIO):
            def read(self, size: int | None = -1) -> bytes:  # noqa: ARG002 (fault injection)
                raise fault

        monkeypatch.setattr(
            tempfile,
            "SpooledTemporaryFile",
            lambda **_kwargs: UnreadableArticle(),
        )
    else:
        status_calls = 0

        def status() -> tuple[int, str]:
            nonlocal status_calls
            status_calls += 1
            if status_calls == 2:
                raise fault
            return real_status()

        monkeypatch.setattr(client, "status", status)

    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(fault_type) as error:
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert error.value is fault
    assert client.socket.fileno() == -1
    assert server.received == (["COMPRESS DEFLATE"] if compressed else []) + [
        "POST" if verb == "POST" else "IHAVE <a@b>"
    ]
    with pytest.raises(nntp.NNTPError, match="closed"):
        client.date()


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_article_write_error_survives_failing_close(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server({verb: ReadArticle(f"{ready} send\r\n".encode(), b"")})
    client = server.client(reader=False)
    real_send = client._sendall  # noqa: SLF001 (exercise the C transport hook)
    real_close = client.close
    fault = OSError("partial article write")

    def send(data: bytes) -> None:
        if data.startswith((b"POST\r\n", b"IHAVE ")):
            real_send(data)
        else:
            real_send(data[:5])
            raise fault

    def close() -> None:
        real_close()
        raise OSError("close failed too")

    monkeypatch.setattr(client, "_sendall", send)
    monkeypatch.setattr(client, "close", close)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(OSError, match="partial article write") as error:
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert error.value is fault
    assert client.socket.fileno() == -1


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_article_invalid_final_status_closes(scripted_server: Start, verb: str) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server(
        {verb: ReadArticle(f"{ready} send\r\n".encode(), b"not a status\r\n")}
    )
    client = server.client(reader=False)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPProtocolError):
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert client.socket.fileno() == -1


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_article_complete_final_refusal_keeps_connection(
    scripted_server: Start, verb: str
) -> None:
    ready = 340 if verb == "POST" else 335
    server = scripted_server(
        {
            verb: ReadArticle(f"{ready} send\r\n".encode(), b"502 refused\r\n"),
            "DATE": b"111 20260102030405\r\n",
        }
    )
    client = server.client(reader=False)
    args = ("<a@b>",) if verb == "IHAVE" else ()
    with pytest.raises(nntp.NNTPPermanentError) as error:
        getattr(client, verb.lower())(*args, body=b"article\n")
    assert error.value.code == 502
    assert client.date().year == 2026


def test_overview_discovery_while_reply_held_does_not_poison_cache(
    scripted_server: Start,
) -> None:
    server = scripted_server(
        {
            "CAPABILITIES": b"101 caps\r\nVERSION 2\r\n.\r\n",
            "LIST OVERVIEW.FMT": b"215 fmt\r\nSubject:\r\nXref:full\r\n.\r\n",
            "OVER": b"224 overview\r\n1\tsubject\tXref: host local.test:1\r\n.\r\n",
        }
    )
    client = server.client(reader=False)
    pending = client.capabilities()
    with pytest.raises(nntp.NNTPSyncError):
        client.over(1)
    assert "overview_fmt" not in client.__dict__
    assert "_overview_full_fields" not in client.__dict__
    assert hasattr(pending, "close")
    pending.close()
    number, fields = next(client.over(1))
    assert number == 1
    assert fields["Xref"] == "host local.test:1"
    assert server.received == ["CAPABILITIES", "LIST OVERVIEW.FMT", "OVER 1"]


@pytest.mark.parametrize(
    "fault",
    [
        nntp.NNTPSyncError("reply held"),
        nntp.NNTPTemporaryError(480, "authenticate"),
        nntp.NNTPTimeoutError("read timed out"),
        nntp.NNTPDataError("bad overview layout"),
    ],
)
def test_overview_transient_failure_is_uncached(
    scripted_server: Start, monkeypatch: pytest.MonkeyPatch, fault: nntp.NNTPError
) -> None:
    client = scripted_server().client(reader=False)
    calls = 0

    def layout() -> Iterator[tuple[str, bool]]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise fault
        return iter([("Subject", False), ("Xref", True)])

    monkeypatch.setattr(client, "list_overview_fmt", layout)
    with pytest.raises(type(fault)) as error:
        _ = client.overview_fmt
    assert error.value is fault
    assert "overview_fmt" not in client.__dict__
    assert "_overview_full_fields" not in client.__dict__
    assert client.overview_fmt == ("Subject", "Xref")
    assert client.overview_fmt == ("Subject", "Xref")
    assert calls == 2


@pytest.mark.parametrize("code", [500, 501, 503])
def test_overview_permanent_failure_still_caches_fallback(
    scripted_server: Start, code: int
) -> None:
    server = scripted_server({"LIST OVERVIEW.FMT": f"{code} unsupported\r\n".encode()})
    client = server.client(reader=False)
    assert client.overview_fmt == (
        "Subject",
        "From",
        "Date",
        "Message-ID",
        "References",
        "Bytes",
        "Lines",
    )
    assert client.overview_fmt == client.overview_fmt
    assert server.received == ["LIST OVERVIEW.FMT"]


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_article_relays_surrogateescaped_headers(
    scripted_server: Start, verb: str
) -> None:
    ready, accepted = (340, 240) if verb == "POST" else (335, 235)
    server = scripted_server(
        {
            "HEAD": (
                b"221 0 <a@b> head\r\nSubject: Gr\xfc\xdfe\r\n"
                b"Message-ID: <a@b>\r\n.\r\n"
            ),
            "BODY": b"222 0 <a@b> body\r\nbody\r\n.\r\n",
            verb: ReadArticle(
                f"{ready} send\r\n".encode(), f"{accepted} ok\r\n".encode()
            ),
        }
    )
    client = server.client(reader=False)
    headers = client.head("<a@b>")
    body = client.body("<a@b>", decode=False)
    assert "\udcfc" in headers["Subject"]
    args = ("<a@b>",) if verb == "IHAVE" else ()
    assert getattr(client, verb.lower())(*args, headers, body) is True
    assert server.articles == [
        [b"Subject: Gr\xfc\xdfe\r\n", b"Message-ID: <a@b>\r\n", b"\r\n", b"body\r\n"]
    ]


@pytest.mark.parametrize("errors", ["strict", "replace"])
def test_article_header_encoding_respects_configured_errors(
    scripted_server: Start, errors: str
) -> None:
    server = scripted_server({"POST": ReadArticle(b"340 send\r\n", b"240 ok\r\n")})
    client = server.client(reader=False)
    client.encoding, client.errors = "ascii", errors
    if errors == "strict":
        with pytest.raises(UnicodeEncodeError):
            client.post({"Subject": "caf\u00e9"})
        assert server.received == []
    else:
        assert client.post({"Subject": "caf\u00e9"}) is True
        assert server.articles == [[b"Subject: caf?\r\n", b"\r\n"]]
