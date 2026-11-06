"""Offline tests for the reading layer (region A): multi-line replies."""

from __future__ import annotations

import binascii
import gzip
import zlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

import nntp
from tests.scripted import Raw, StartCompression

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.scripted import ScriptedServer

    Start = Callable[..., ScriptedServer]

DATE = b"111 20260102030405\r\n"
DATE_VALUE = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

# Lines as sent on the wire (dot-stuffed) and as the client must return them.
STUFFED = b"plain\r\n..dot\r\n..\r\n...\r\n.. two\r\nend.\r\n"
UNSTUFFED = b"plain\r\n.dot\r\n.\r\n..\r\n. two\r\nend.\r\n"
STUFFED_HELP = b"100 help\r\n" + STUFFED + b".\r\n"


def test_body_dot_unstuffing(scripted_server: Start) -> None:
    server = scripted_server(
        {"BODY": b"222 0 <a@b> body\r\n" + STUFFED + b".\r\n", "DATE": DATE}
    )
    client = server.client()
    assert client.body("<a@b>", decode=False) == UNSTUFFED
    assert client.date() == DATE_VALUE


def test_info_dot_unstuffing(scripted_server: Start) -> None:
    server = scripted_server({"HELP": b"100 help\r\n" + STUFFED + b".\r\n"})
    client = server.client()
    assert client.help() == UNSTUFFED.decode()


def test_dot_unstuffing_split_reads(scripted_server: Start) -> None:
    """A stuffed line split over two reads is still unstuffed once."""
    server = scripted_server(
        {"HELP": [b"100 help\r\n.", 0.05, b".dot\r\n", 0.05, b".\r\n"]}
    )
    client = server.client()
    assert client.help() == ".dot\r\n"


def _gzip_list(payload: bytes) -> bytes:
    return b"215 list follows [COMPRESS=GZIP]\r\n" + payload


def test_gzip_terminator_inside(scripted_server: Start) -> None:
    """XFEATURE COMPRESS GZIP TERMINATOR: the terminator is compressed too."""
    reply = _gzip_list(gzip.compress(STUFFED + b".\r\n"))
    server = scripted_server({"LIST": reply, "DATE": DATE})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode()
    assert client.date() == DATE_VALUE


def test_gzip_terminator_inside_split_trailer(scripted_server: Start) -> None:
    """The gzip trailer arrives after the decompressed terminator (review: sol).

    The 8-byte trailer must be read as part of this reply, not of the next.
    """
    blob = gzip.compress(STUFFED + b".\r\n")
    reply = [_gzip_list(blob[:-8]), 0.05, blob[-8:]]
    server = scripted_server({"LIST": reply, "DATE": DATE})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode()
    assert client.date() == DATE_VALUE


def test_gzip_terminator_inside_next_reply_follows(scripted_server: Start) -> None:
    """Bytes after the gzip stream are the start of the next reply."""
    blob = gzip.compress(STUFFED + b".\r\n")
    reply = [_gzip_list(blob[:-3]), 0.05, blob[-3:] + DATE]
    server = scripted_server({"LIST": reply, "DATE": b""})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode()
    assert client.date() == DATE_VALUE


def test_gzip_terminator_after_same_read(scripted_server: Start) -> None:
    """The terminator follows the gzip stream, in the same packet."""
    reply = _gzip_list(gzip.compress(STUFFED) + b".\r\n")
    server = scripted_server({"LIST": reply, "DATE": DATE})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode()
    assert client.date() == DATE_VALUE


def test_gzip_terminator_after_later_read(scripted_server: Start) -> None:
    """The terminator follows the gzip stream in later packets.

    Before the fix, the bytes after the stream were added again on every read,
    so lines came back twice.
    """
    blob = gzip.compress(STUFFED)
    reply = [_gzip_list(blob[:10]), 0.05, blob[10:], 0.05, b"..x\r\n", 0.05, b".\r\n"]
    server = scripted_server({"LIST": reply, "DATE": DATE})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode() + ".x\r\n"
    assert client.date() == DATE_VALUE


def test_gzip_bytes_after_terminator_kept(scripted_server: Start) -> None:
    """Bytes after the terminator are the start of the next reply."""
    reply = _gzip_list(gzip.compress(STUFFED) + b".\r\n" + DATE)
    server = scripted_server({"LIST": reply, "DATE": b""})
    client = server.client()
    assert "".join(client.list()) == UNSTUFFED.decode()
    assert client.date() == DATE_VALUE


def _yenc_lines(data: bytes, linelen: int = 128) -> list[bytes]:
    lines, line = [], bytearray()
    for byte in data:
        enc = (byte + 42) & 0xFF
        if enc in (0x00, 0x0A, 0x0D, 0x3D):
            line += bytes([0x3D, (enc + 64) & 0xFF])
        else:
            line.append(enc)
        if len(line) >= linelen:
            lines.append(bytes(line))
            line = bytearray()
    if line:
        lines.append(bytes(line))
    return lines


def test_yenc_body_with_dot_lines(scripted_server: Start) -> None:
    """Issue #99: encoded lines starting with '.' decoded twice."""
    # Byte 4 encodes to '.'. No byte needs escaping, so every encoded line is
    # 128 bytes long and starts with a dot.
    escaped = {19, 214, 224, 227}  # encode to NUL, LF, CR, '='
    data = bytes(
        4 if i % 128 == 0 else (1 if i % 256 in escaped else i % 256)
        for i in range(1024)
    )
    encoded = _yenc_lines(data)
    assert all(line.startswith(b".") for line in encoded)
    crc = binascii.crc32(data)
    lines = [
        b"=ybegin part=1 total=1 line=128 size=%d name=x.bin" % len(data),
        b"=ypart begin=1 end=%d" % len(data),
        *encoded,
        b"=yend size=%d part=1 pcrc32=%08x" % (len(data), crc),
    ]
    wire = b"".join((b"." + x if x.startswith(b".") else x) + b"\r\n" for x in lines)
    server = scripted_server({"BODY": b"222 0 <a@b> body\r\n" + wire + b".\r\n"})
    client = server.client()
    assert client.body("<a@b>") == data


# Abandoned and failed replies (bug 5): the connection must stay usable.

ACTIVE = b"215 list follows\r\na.one 2 1 y\r\na.two 2 1 y\r\na.three 2 1 y\r\n.\r\n"


def test_break_out_of_reply(scripted_server: Start) -> None:
    server = scripted_server({"LIST ACTIVE": ACTIVE, "DATE": DATE})
    client = server.client()
    for _group in client.list_active():
        break
    assert client.date() == DATE_VALUE


def test_next_once(scripted_server: Start) -> None:
    server = scripted_server(
        {"CAPABILITIES": b"101 caps\r\nVERSION 2\r\nREADER\r\n.\r\n", "DATE": DATE}
    )
    client = server.client()
    assert next(client.capabilities()) == "VERSION 2"
    assert client.date() == DATE_VALUE


def test_parse_error_inside_reply(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST ACTIVE.TIMES": b"215 times\r\nbad\r\nmore 1 x\r\n.\r\n",
            "DATE": DATE,
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError):
        list(client.list_active_times())
    assert client.date() == DATE_VALUE


def test_caller_error_inside_loop(scripted_server: Start) -> None:
    server = scripted_server({"LIST ACTIVE": ACTIVE, "DATE": DATE})
    client = server.client()
    with pytest.raises(KeyError):
        _fail_in_loop(client)
    assert client.date() == DATE_VALUE


def _fail_in_loop(client: nntp.NNTPClient) -> None:
    for _group in client.list_active():
        raise KeyError


def test_reply_still_held_is_active(scripted_server: Start) -> None:
    """A reply someone still reads blocks other commands, as before."""
    server = scripted_server({"LIST ACTIVE": ACTIVE, "DATE": DATE})
    client = server.client()
    groups = client.list_active()
    assert next(groups).name == "a.one"
    with pytest.raises(nntp.nntp.NNTPSyncError):  # exported by B6
        client.date()
    assert [group.name for group in groups] == ["a.two", "a.three"]
    assert client.date() == DATE_VALUE


def test_with_block_break(scripted_server: Start) -> None:
    server = scripted_server({"LIST ACTIVE": ACTIVE})
    with server.client() as client:
        for _group in client.list_active():
            break
    assert server.received[-1] == "QUIT"


def test_with_block_user_error_propagates(scripted_server: Start) -> None:
    server = scripted_server({"LIST ACTIVE": ACTIVE})
    with pytest.raises(KeyError):
        _fail_in_with_block(server)
    # whether QUIT is sent on the way out is region B's business (B1)


def _fail_in_with_block(server: ScriptedServer) -> None:
    with server.client() as client:
        _fail_in_loop(client)


ARTICLE = (
    b"220 1 <a@b> article\r\n"
    b"Subject: hello\r\nFrom: x <x@y>\r\n\r\n"
    b"body line\r\n..dot\r\n.\r\n"
)


def test_article_headers_and_body(scripted_server: Start) -> None:
    server = scripted_server({"ARTICLE": ARTICLE, "DATE": DATE})
    client = server.client()
    number, headers, body = client.article("<a@b>", decode=False)
    assert number == 1
    assert headers["Subject"] == "hello"
    assert body == b"body line\r\n.dot\r\n"
    assert client.date() == DATE_VALUE


def test_article_bad_headers(scripted_server: Start) -> None:
    """A header parse error must not leave the body on the connection."""
    reply = b"220 1 <a@b> article\r\n continuation first\r\n\r\nbody\r\n.\r\n"
    server = scripted_server({"ARTICLE": reply, "DATE": DATE})
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="continuation"):
        client.article("<a@b>")
    assert client.date() == DATE_VALUE


def test_head_bad_headers(scripted_server: Start) -> None:
    """Header parse errors are NNTPDataError (REVIEW.md Low list)."""
    reply = b"221 1 <a@b> head\r\nno colon here\r\n.\r\n"
    server = scripted_server({"HEAD": reply, "DATE": DATE})
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="Invalid article headers"):
        client.head("<a@b>")
    assert client.date() == DATE_VALUE


def test_head(scripted_server: Start) -> None:
    reply = b"221 1 <a@b> head\r\nSubject: hello\r\n.\r\n"
    server = scripted_server({"HEAD": reply, "DATE": DATE})
    client = server.client()
    assert client.head("<a@b>")["Subject"] == "hello"
    assert client.date() == DATE_VALUE


def test_gzip_abandoned(scripted_server: Start) -> None:
    blob = gzip.compress(STUFFED + b".\r\n")
    reply = [_gzip_list(blob[:-8]), 0.05, blob[-8:]]
    server = scripted_server({"LIST": reply, "DATE": DATE})
    client = server.client()
    assert next(client.list()) == "plain\r\n"
    assert client.date() == DATE_VALUE


def _xzver_reply(text: bytes, *, crc: int | None = None) -> bytes:
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = deflate.compress(text) + deflate.flush()
    lines = _yenc_lines(data)
    crc = binascii.crc32(data) if crc is None else crc
    wire = [
        b"=ybegin line=128 size=%d name=xzver" % len(data),
        *lines,
        b"=yend size=%d crc32=%08x" % (len(data), crc),
    ]
    stuffed = b"".join((b"." + x if x.startswith(b".") else x) + b"\r\n" for x in wire)
    return b"224 compressed overview\r\n" + stuffed + b".\r\n"


OVERVIEW = (
    b"1\tsubject one\tx@y\tdate\t<1@y>\t\t10\t1\r\n"
    b"2\tsubject two\tx@y\tdate\t<2@y>\t\t10\t1\r\n"
)
OVERVIEW_FMT = (
    b"215 fmt\r\nSubject:\r\nFrom:\r\nDate:\r\nMessage-ID:\r\n"
    b"References:\r\nBytes:\r\nLines:\r\n.\r\n"
)


def test_xzver(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": OVERVIEW_FMT,
            "XZVER": _xzver_reply(OVERVIEW),
            "DATE": DATE,
        }
    )
    client = server.client()
    entries = list(client.xzver((1, 2)))
    assert [(n, h["Subject"]) for n, h in entries] == [
        (1, "subject one"),
        (2, "subject two"),
    ]
    assert client.date() == DATE_VALUE


def test_xzver_abandoned_and_bad_crc(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": OVERVIEW_FMT,
            "XZVER 1-2": _xzver_reply(OVERVIEW),
            "XZVER 1-": _xzver_reply(OVERVIEW, crc=0),
            "DATE": DATE,
        }
    )
    client = server.client()
    assert next(client.xzver((1, 2)))[0] == 1
    assert client.date() == DATE_VALUE
    with pytest.raises(nntp.NNTPDataError, match="CRC"):
        list(client.xzver((1,)))
    assert client.date() == DATE_VALUE


def test_unexpected_multiline_code_is_drained(scripted_server: Start) -> None:
    server = scripted_server({"HDR": b"221 old-style\r\n1 subj\r\n.\r\n", "DATE": DATE})
    client = server.client()
    # as if a command got a multi-line success code it didn't expect
    client.socket.sendall(b"HDR Subject\r\n")
    code, message = client.status()
    error = client._unexpected(code, message)  # noqa: SLF001
    assert isinstance(error, nntp.NNTPReplyError)
    assert error.code == 221
    assert client.date() == DATE_VALUE


def test_reply_registered_before_first_read(scripted_server: Start) -> None:
    """A reply returned but not yet iterated still blocks (review: terra)."""
    server = scripted_server({"LIST": ACTIVE, "DATE": DATE})
    client = server.client()
    reply = client.list()
    with pytest.raises(nntp.nntp.NNTPSyncError):
        client.date()
    del reply
    assert client.date() == DATE_VALUE


def test_reply_returned_and_dropped(scripted_server: Start) -> None:
    server = scripted_server({"LIST": ACTIVE, "DATE": DATE})
    client = server.client()
    client.list()
    assert client.date() == DATE_VALUE


def _corrupt_gzip_list() -> list[bytes | float]:
    blob = bytearray(gzip.compress(b"alpha\r\nbeta\r\n", mtime=0))
    blob[-8] ^= 1  # break the CRC in the gzip trailer
    return [_gzip_list(bytes(blob[:-8])), 0.05, bytes(blob[-8:]), 0.05, b".\r\n"]


def test_gzip_corrupt_abandoned_closes(scripted_server: Start) -> None:
    """Corrupt gzip: the reply's end is unknown, so the connection is closed.

    Review: sol. Before, the next command read the rest of the bad reply.
    """
    server = scripted_server({"LIST": _corrupt_gzip_list(), "DATE": DATE})
    client = server.client()
    assert next(client.list()) == "alpha\r\n"
    with pytest.raises(nntp.NNTPDataError, match="connection closed"):
        client.date()
    assert client.socket.fileno() == -1
    assert "DATE" not in server.received


def test_gzip_corrupt_read_closes(scripted_server: Start) -> None:
    server = scripted_server({"LIST": _corrupt_gzip_list(), "DATE": DATE})
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="connection closed"):
        list(client.list())
    assert client.socket.fileno() == -1


# yEnc size and CRC checks (A3)

YDATA = bytes(range(256)) * 3


def _yenc_body(
    data: bytes,
    *,
    begin: bytes = b"=ybegin line=128 size=%(size)d name=x.bin",
    part: bytes | None = None,
    end: bytes = b"=yend size=%(size)d crc32=%(crc)08x",
    after: bytes = b"",
    size: int | None = None,
    crc: int | None = None,
) -> bytes:
    values = {
        b"size": len(data) if size is None else size,
        b"crc": binascii.crc32(data) if crc is None else crc,
    }
    lines = [begin % values]
    if part is not None:
        lines.append(part % values)
    lines += [*_yenc_lines(data), end % values]
    wire = b"".join((b"." + x if x.startswith(b".") else x) + b"\r\n" for x in lines)
    return b"222 0 <a@b> body\r\n" + wire + after + b".\r\n"


def _body_server(scripted_server: Start, reply: bytes) -> nntp.NNTPClient:
    return scripted_server({"BODY": reply, "DATE": DATE}).client()


def test_yenc_single_part_ok(scripted_server: Start) -> None:
    client = _body_server(scripted_server, _yenc_body(YDATA))
    assert client.body("<a@b>") == YDATA
    assert client.date() == DATE_VALUE


def test_yenc_bad_crc(scripted_server: Start) -> None:
    client = _body_server(scripted_server, _yenc_body(YDATA, crc=0x12345678))
    with pytest.raises(nntp.NNTPDataError, match="CRC"):
        client.body("<a@b>")
    assert client.date() == DATE_VALUE  # the reply was read to its end


def test_yenc_bad_size(scripted_server: Start) -> None:
    client = _body_server(scripted_server, _yenc_body(YDATA, size=len(YDATA) + 1))
    with pytest.raises(nntp.NNTPDataError, match="size"):
        client.body("<a@b>")
    assert client.date() == DATE_VALUE


def test_yenc_missing_trailer(scripted_server: Start) -> None:
    reply = _yenc_body(YDATA).replace(b"=yend", b"not a trailer")
    client = _body_server(scripted_server, reply)
    with pytest.raises(nntp.NNTPDataError, match="trailer"):
        client.body("<a@b>")
    assert client.date() == DATE_VALUE


def test_yenc_multipart_pcrc32(scripted_server: Start) -> None:
    """In a part, pcrc32 is checked; crc32 is the whole file's CRC."""
    reply = _yenc_body(
        YDATA,
        begin=b"=ybegin part=2 total=3 line=128 size=9999 name=x.bin",
        part=b"=ypart begin=769 end=%(size)d",
        end=b"=yend size=%(size)d part=2 pcrc32=%(crc)08x crc32=deadbeef",
    )
    client = _body_server(scripted_server, reply)
    assert client.body("<a@b>") == YDATA


def test_yenc_multipart_bad_pcrc32(scripted_server: Start) -> None:
    reply = _yenc_body(
        YDATA,
        begin=b"=ybegin part=2 total=3 line=128 size=9999 name=x.bin",
        part=b"=ypart begin=769 end=%(size)d",
        end=b"=yend size=%(size)d part=2 pcrc32=00000001",
    )
    client = _body_server(scripted_server, reply)
    with pytest.raises(nntp.NNTPDataError, match="CRC"):
        client.body("<a@b>")


def test_yenc_multipart_crc32_only_not_checked(scripted_server: Start) -> None:
    """A part with only the whole file's crc32 can't be checked."""
    reply = _yenc_body(
        YDATA,
        begin=b"=ybegin part=3 total=3 line=128 size=9999 name=x.bin",
        part=b"=ypart begin=1 end=%(size)d",
        end=b"=yend size=%(size)d part=3 crc32=deadbeef",
    )
    client = _body_server(scripted_server, reply)
    assert client.body("<a@b>") == YDATA


def test_yenc_short_crc_and_text_after_trailer(scripted_server: Start) -> None:
    """CRCs without leading zeros; text after =yend is not decoded."""
    data = b"\x00" * 3 + b"abc"
    crc = binascii.crc32(data)
    reply = _yenc_body(
        data,
        end=b"=yend size=%(size)d crc32=" + (b"%x" % crc).lstrip(b"0"),
        after=b"-- \r\nsignature\r\n",
    )
    client = _body_server(scripted_server, reply)
    assert client.body("<a@b>") == data


@pytest.mark.parametrize(
    ("end", "match"),
    [
        (b"=yend size=%(size)dgarbage crc32=%(crc)08x", "valid size"),
        (b"=yend crc32=%(crc)08x", "valid size"),
        (b"=yend size=ab crc32=0", "valid size"),
        (b"=yend size=%(size)d crc32=0garbage", "invalid CRC"),
        (b"=yend size=%(size)d crc32=123456789", "invalid CRC"),
        (b"=yend size=%(size)d part=x pcrc32=%(crc)08x", "invalid part"),
    ],
)
def test_yenc_malformed_trailer(scripted_server: Start, end: bytes, match: str) -> None:
    """Review: sol. Malformed trailers raise NNTPDataError, not ValueError."""
    client = _body_server(scripted_server, _yenc_body(YDATA, end=end))
    with pytest.raises(nntp.NNTPDataError, match=match):
        client.body("<a@b>")
    assert client.date() == DATE_VALUE


def test_text_body_starting_like_yenc(scripted_server: Start) -> None:
    """Only the =ybegin keyword starts yEnc, not a word that begins with it."""
    reply = b"222 0 <a@b> body\r\n=ybeginners guide\r\ntext\r\n.\r\n"
    client = _body_server(scripted_server, reply)
    assert client.body("<a@b>") == b"=ybeginners guide\r\ntext\r\n"


@pytest.mark.parametrize(
    ("verb", "call"),
    [
        ("ARTICLE", lambda c: c.article("<a@b>")),
        ("HEAD", lambda c: c.head("<a@b>")),
        ("BODY", lambda c: c.body("<a@b>")),
    ],
)
def test_article_commands_unexpected_multiline_code(
    scripted_server: Start, verb: str, call: Callable[[nntp.NNTPClient], object]
) -> None:
    """A wrong multi-line success code is drained before raising (I2)."""
    wrong = (
        b"224 overview\r\n1\tsubject\r\n.\r\n"
        if verb != "HEAD"
        else (b"222 0 <a@b> body\r\nbody\r\n.\r\n")
    )
    server = scripted_server({verb: wrong, "DATE": DATE})
    client = server.client()
    with pytest.raises(nntp.NNTPReplyError):
        call(client)
    assert client.date() == DATE_VALUE


@pytest.mark.parametrize(
    "line", [b"\r\n", b"hello\r\n", b"99 too low\r\n", b"6000 x\r\n"]
)
def test_invalid_status_line(scripted_server: Start, line: bytes) -> None:
    """NNTPProtocolError carries a str message, also for an empty line."""
    server = scripted_server({"DATE": line})
    client = server.client()
    with pytest.raises(nntp.NNTPProtocolError) as info:
        client.date()
    assert isinstance(info.value.args[0], str)
    assert info.value.args[0].startswith("Invalid status line")


def test_info_close_before_first_line(scripted_server: Start) -> None:
    """close() on a reply that was never read drops it at once (A7)."""
    server = scripted_server({"HELP": b"100 help\r\nline\r\n.\r\n", "DATE": DATE})
    client = server.client()
    code, message = client.command("HELP")
    reply = client.info(code, message)
    reply.close()  # type: ignore[attr-defined]
    assert client.date() == DATE_VALUE
    assert list(reply) == []


def test_info_close_after_first_line(scripted_server: Start) -> None:
    server = scripted_server({"HELP": b"100 help\r\none\r\ntwo\r\n.\r\n", "DATE": DATE})
    client = server.client()
    code, message = client.command("HELP")
    reply = client.info(code, message)
    assert next(reply) == "one\r\n"
    reply.close()  # type: ignore[attr-defined]
    assert client.date() == DATE_VALUE


def test_read_timeout(scripted_server: Start) -> None:
    """A read timeout is an NNTPTimeoutError (also a TimeoutError); the
    connection is closed, since the late reply would desync the next command."""
    server = scripted_server({"DATE": [1.0, DATE]})
    client = server.client(timeout=1)
    client.socket.settimeout(0.1)
    with pytest.raises(nntp.NNTPTimeoutError) as info:
        client.date()
    assert isinstance(info.value, TimeoutError)
    assert client.socket.fileno() == -1
    with pytest.raises(nntp.NNTPError, match="closed"):
        client.date()


def test_read_timeout_inside_reply(scripted_server: Start) -> None:
    server = scripted_server({"HELP": [b"100 help\r\none\r\n", 1.0, b".\r\n"]})
    client = server.client(timeout=1)
    client.socket.settimeout(0.1)
    with pytest.raises(nntp.NNTPTimeoutError):
        client.help()
    assert client.socket.fileno() == -1


# COMPRESS DEFLATE transport (A10, RFC 8054)


def _compressed(data: bytes) -> bytes:
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    return deflate.compress(data) + deflate.flush(zlib.Z_PARTIAL_FLUSH)


def _start(client: nntp.NNTPClient) -> None:
    code, _message = client.command("COMPRESS DEFLATE")
    assert code == 206
    client._start_compression()  # noqa: SLF001 (region B's compress() comes in B9)


def test_compress_commands_and_replies(scripted_server: Start) -> None:
    server = scripted_server(
        {"COMPRESS DEFLATE": StartCompression(), "DATE": DATE, "HELP": STUFFED_HELP}
    )
    client = server.client()
    assert not client.compressed
    _start(client)
    assert client.compressed
    assert client.date() == DATE_VALUE
    assert client.help() == UNSTUFFED.decode()
    assert server.received[-2:] == ["DATE", "HELP"]  # decompressed by the server


def test_compress_reply_split_over_reads(scripted_server: Start) -> None:
    """Partial DEFLATE blocks are inflated as they arrive."""
    reply = [b"100 help\r\n", 0.05, b"one\r\n..two\r\n", 0.05, b".\r\n"]
    server = scripted_server({"COMPRESS DEFLATE": StartCompression(), "HELP": reply})
    client = server.client()
    _start(client)
    assert client.help() == "one\r\n.two\r\n"


def test_compress_tail_in_same_read_as_206(scripted_server: Start) -> None:
    """Bytes after the 206 line in the same packet are compressed (review: sol)."""
    tail = _compressed(DATE)
    server = scripted_server(
        {"COMPRESS DEFLATE": [Raw(b"206 compression active\r\n" + tail)]}
    )
    client = server.client()
    code, _message = client.command("COMPRESS DEFLATE")
    assert code == 206
    client._start_compression()  # noqa: SLF001
    # the DATE reply was already sent; read it without sending a command
    assert client.status() == (111, "20260102030405")


def test_compress_corrupt_stream_closes(scripted_server: Start) -> None:
    server = scripted_server(
        {"COMPRESS DEFLATE": StartCompression(), "DATE": [Raw(b"\xff\xfe garbage")]}
    )
    client = server.client()
    _start(client)
    with pytest.raises(nntp.NNTPDataError, match="COMPRESS stream corrupt"):
        client.date()
    assert client.socket.fileno() == -1


def test_compress_twice_refused(scripted_server: Start) -> None:
    server = scripted_server({"COMPRESS DEFLATE": StartCompression()})
    client = server.client()
    _start(client)
    with pytest.raises(nntp.NNTPError, match="already active"):
        client._start_compression()  # noqa: SLF001


def _finished(data: bytes) -> bytes:
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    return deflate.compress(data) + deflate.flush(zlib.Z_FINISH)


def test_compress_data_after_stream_end_closes(scripted_server: Start) -> None:
    """Bytes after the end of the DEFLATE stream are corrupt (review: terra)."""
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            "DATE": [Raw(_finished(DATE) + b"garbage")],
        }
    )
    client = server.client()
    _start(client)
    with pytest.raises(nntp.NNTPDataError, match="COMPRESS stream corrupt"):
        client.date()
    assert client.socket.fileno() == -1


def test_compress_tail_after_stream_end_closes(scripted_server: Start) -> None:
    server = scripted_server(
        {
            "COMPRESS DEFLATE": [
                Raw(b"206 compression active\r\n" + _finished(DATE) + b"garbage")
            ]
        }
    )
    client = server.client()
    code, _message = client.command("COMPRESS DEFLATE")
    assert code == 206
    with pytest.raises(nntp.NNTPDataError, match="COMPRESS stream corrupt"):
        client._start_compression()  # noqa: SLF001
    assert client.socket.fileno() == -1


def test_compress_bytes_in_later_read_after_stream_end(scripted_server: Start) -> None:
    """The stream ends cleanly, garbage follows in a later read (review: sol)."""
    server = scripted_server(
        {
            "COMPRESS DEFLATE": StartCompression(),
            "DATE": [Raw(_finished(DATE))],
            "HELP": [Raw(b"garbage")],
        }
    )
    client = server.client()
    _start(client)
    assert client.date() == DATE_VALUE  # the last reply of the stream is fine
    with pytest.raises(nntp.NNTPDataError, match="COMPRESS stream corrupt"):
        client.help()
    assert client.socket.fileno() == -1


# Release cross review (R1)


def test_article_plain_body_with_yenc_in_subject(scripted_server: Start) -> None:
    """The Subject doesn't switch on yEnc decoding; the body decides (X1-01)."""
    article = (
        b"220 1 <a@b> article\r\nSubject: Question about yEnc\r\n\r\n"
        b"Hello world!\r\n.\r\n"
    )
    server = scripted_server(
        {
            "ARTICLE": article,
            "BODY": article.replace(
                b"220 1 <a@b> article\r\nSubject: Question about yEnc\r\n\r\n",
                b"222 1 <a@b> body\r\n",
            ),
        }
    )
    client = server.client()
    assert client.article("<a@b>")[2] == b"Hello world!\r\n"
    assert client.body("<a@b>") == b"Hello world!\r\n"


def test_article_yenc_body_detected(scripted_server: Start) -> None:
    body = _yenc_body(YDATA).split(b"\r\n", 1)[1]
    article = b"220 1 <a@b> article\r\nSubject: a file\r\n\r\n" + body
    server = scripted_server({"ARTICLE": article, "DATE": DATE})
    client = server.client()
    assert client.article("<a@b>")[2] == YDATA
    assert client.date() == DATE_VALUE


def test_forced_decode_without_ybegin(scripted_server: Start) -> None:
    client = _body_server(scripted_server, b"222 0 <a@b> body\r\nplain\r\n.\r\n")
    with pytest.raises(nntp.NNTPDataError, match="=ybegin"):
        client.body("<a@b>", decode=True)
    assert client.date() == DATE_VALUE


@pytest.mark.parametrize("status", [b"220 bad <a@b> article", b"220"])
def test_article_bad_status_drains(scripted_server: Start, status: bytes) -> None:
    """A bad article number in the 220 line doesn't leave the article (X1-03)."""
    article = status + b"\r\nSubject: s\r\n\r\nbody\r\n.\r\n"
    server = scripted_server({"ARTICLE": article, "DATE": DATE})
    client = server.client()
    with pytest.raises(nntp.NNTPProtocolError, match="Invalid ARTICLE status"):
        client.article("<a@b>")
    assert client.date() == DATE_VALUE


def test_info_decode_error_releases_reply(scripted_server: Start) -> None:
    """A decoding error doesn't keep the reply registered while it's held (X1-05)."""
    server = scripted_server(
        {"HELP": b"100 help\r\n\xffbad\r\nrest\r\n.\r\n", "DATE": DATE}
    )
    client = server.client()
    client.errors = "strict"
    code, message = client.command("HELP")
    try:
        list(client.info(code, message))
    except UnicodeDecodeError as exc:
        held = exc  # keeps the traceback, and with it the reply, alive
    assert held.__traceback__ is not None
    client.errors = "surrogateescape"
    assert client.date() == DATE_VALUE


def test_xzver_truncated_stream(scripted_server: Start) -> None:
    """Cut DEFLATE data in a valid yEnc wrapper raises, not partial rows (X1-04)."""
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = (deflate.compress(OVERVIEW) + deflate.flush())[:-4]
    wire = [
        b"=ybegin line=128 size=%d name=xzver" % len(data),
        *_yenc_lines(data),
        b"=yend size=%d crc32=%08x" % (len(data), binascii.crc32(data)),
    ]
    stuffed = b"".join((b"." + x if x.startswith(b".") else x) + b"\r\n" for x in wire)
    server = scripted_server(
        {
            "LIST OVERVIEW.FMT": OVERVIEW_FMT,
            "XZVER": b"224 compressed overview\r\n" + stuffed + b".\r\n",
            "DATE": DATE,
        }
    )
    client = server.client()
    with pytest.raises(nntp.NNTPDataError, match="partial line"):
        list(client.xzver((1, 2)))
    assert client.date() == DATE_VALUE


@pytest.mark.parametrize("code", [b"+111", b"0111", b"1_11", b"11"])
def test_status_code_three_digits(scripted_server: Start, code: bytes) -> None:
    """Only three ASCII digits are a status code (X1-08)."""
    server = scripted_server({"DATE": code + b" 20260102030405\r\n"})
    client = server.client()
    with pytest.raises(nntp.NNTPProtocolError, match="Invalid status line"):
        client.date()
