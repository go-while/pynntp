"""Offline tests for the reading layer (region A): multi-line replies."""

from __future__ import annotations

import binascii
import gzip
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.scripted import ScriptedServer

    Start = Callable[..., ScriptedServer]

DATE = b"111 20260102030405\r\n"
DATE_VALUE = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

# Lines as sent on the wire (dot-stuffed) and as the client must return them.
STUFFED = b"plain\r\n..dot\r\n..\r\n...\r\n.. two\r\nend.\r\n"
UNSTUFFED = b"plain\r\n.dot\r\n.\r\n..\r\n. two\r\nend.\r\n"


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
