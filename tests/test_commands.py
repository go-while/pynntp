"""Offline tests for commands and parsing (region C)."""

from __future__ import annotations

import binascii
import gzip
import zlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

import nntp
from nntp.types import Newsgroup
from tests.scripted import ReadArticle

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
