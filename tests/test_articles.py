"""ARTICLE, HEAD and BODY, including yEnc decoding and checks."""

from __future__ import annotations

import gzip
import zlib

import pytest

import nntp
from tests.helpers import (
    DATE,
    MODE_READER,
    PLAIN,
    WELCOME,
    XFEATURE_OK,
    Connect,
    dot_stuff,
    yenc_body,
    yenc_encode,
)


def test_body_dot_unstuffing(connect: Connect) -> None:
    client, _ = connect(
        WELCOME + MODE_READER + b"222 1 <a@b>\r\nline\r\n..dotted\r\n.\r\n"
    )
    assert client.body(1) == b"line\r\n.dotted\r\n"


def test_body_yenc_autodetect(connect: Connect) -> None:
    # 0x04 encodes to ".", so each of the first lines starts with a dot.
    plain = (b"\x04" + b"a" * 127) * 4 + bytes(range(256)) * 4
    encoded = yenc_encode(plain)
    assert encoded.startswith(b".")
    size = len(plain)
    server = (
        f"222 1 <a@b>\r\n=ybegin line=128 size={size} name=x\r\n".encode()
        + dot_stuff(encoded)
        + f"=yend size={size} crc32={zlib.crc32(plain):08x}\r\n.\r\n".encode()
    )
    client, _ = connect(WELCOME + MODE_READER + server)
    assert client.body(1) == plain


def test_article(connect: Connect) -> None:
    client, _ = connect(
        WELCOME
        + MODE_READER
        + b"220 5 <a@b>\r\nSubject: hi\r\nFrom: me\r\n\r\nbody\r\n.\r\n"
    )
    articleno, headers, body = client.article(5)
    assert articleno == 5
    assert headers["subject"] == "hi"
    assert body == b"body\r\n"


@pytest.mark.parametrize("status", [b"220", b"220 x <a@b>"])
def test_article_bad_status(connect: Connect, status: bytes) -> None:
    article = status + b"\r\nSubject: s\r\n\r\nbody\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + article + DATE)
    with pytest.raises(nntp.NNTPDataError, match="Invalid ARTICLE status"):
        client.article()
    assert client.date().year == 2024  # The article was read; in sync


@pytest.mark.parametrize("part", [None, 2])
def test_yenc_valid(connect: Connect, part: int | None) -> None:
    client, _ = connect(WELCOME + MODE_READER + yenc_body(PLAIN, part=part))
    assert client.body(1) == PLAIN


@pytest.mark.parametrize(
    ("part", "trailer", "match"),
    [
        (None, "size=768 crc32=00000001", "CRC32 is"),
        (None, "size=767 crc32=00000001", "decoded 768 bytes, trailer says 767"),
        (2, "size=768 part=2 pcrc32=00000001", "CRC32 is"),
    ],
)
def test_yenc_mismatch_keeps_connection(
    connect: Connect, part: int | None, trailer: str, match: str
) -> None:
    server = yenc_body(PLAIN, part=part, trailer=trailer) + DATE
    client, _ = connect(WELCOME + MODE_READER + server)
    with pytest.raises(nntp.NNTPYEncError, match=match) as info:
        client.body(1)
    assert info.value.data == PLAIN  # Kept for e.g. par2 repair
    assert isinstance(info.value, nntp.NNTPDataError)
    assert client.date().year == 2024  # Whole response was read; still in sync


def test_yenc_missing_trailer(connect: Connect) -> None:
    client, _ = connect(WELCOME + MODE_READER + yenc_body(PLAIN, end=False))
    with pytest.raises(nntp.NNTPDataError, match="missing =yend"):
        client.body(1)


def test_yenc_trailer_without_crc_checks_size_only(connect: Connect) -> None:
    server = yenc_body(PLAIN, trailer="size=768")
    client, _ = connect(WELCOME + MODE_READER + server)
    assert client.body(1) == PLAIN


def test_yenc_article_validated(connect: Connect) -> None:
    body = yenc_body(PLAIN, trailer="size=768 crc32=00000001")
    article = (
        b"220 1 <a@b>\r\nSubject: file yEnc (1/1)\r\n\r\n" + body.split(b"\r\n", 1)[1]
    )
    client, _ = connect(WELCOME + MODE_READER + article)
    with pytest.raises(nntp.NNTPDataError, match="CRC32"):
        client.article(1)


def test_body_detection_leading_blank_lines(connect: Connect) -> None:
    yenc = yenc_body(PLAIN).replace(b"222 1 <a@b>\r\n", b"222 1 <a@b>\r\n\r\n\r\n", 1)
    plain = b"222 2 <b@c>\r\n\r\nhello\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + yenc + plain + DATE)
    assert client.body(1) == PLAIN  # Blank lines before yEnc are dropped
    assert client.body(2) == b"\r\nhello\r\n"  # Kept in a plain body
    assert client.date().year == 2024


def test_body_decode_forced(connect: Connect) -> None:
    raw = yenc_encode(b"raw bytes")  # No =ybegin/=yend lines at all
    server = b"222 1 <a@b>\r\n" + raw + b".\r\n" + b"222 2 <b@c>\r\n=ybegin x\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + server + DATE)
    with pytest.raises(nntp.NNTPYEncError, match="no =ybegin"):
        client.body(1, decode=True)
    assert client.body(2, decode=False) == b"=ybegin x\r\n"
    assert client.date().year == 2024


def test_yenc_text_outside_block_dropped(connect: Connect) -> None:
    body = yenc_body(PLAIN)[:-3] + b"-- \r\nsig\r\n.\r\n"  # After =yend
    client, _ = connect(WELCOME + MODE_READER + body)
    assert client.body(1) == PLAIN


def test_body_decode_forced_ybegin_prefix_is_not_a_block(connect: Connect) -> None:
    server = b"222 1 <a@b>\r\n=ybeginners guide\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + server)
    with pytest.raises(nntp.NNTPYEncError, match="no =ybegin"):
        client.body(1, decode=True)


def test_body_ybegin_prefix_is_plain(connect: Connect) -> None:
    server = b"222 1 <a@b>\r\n=ybeginners guide\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + server)
    assert client.body(1) == b"=ybeginners guide\r\n"


def test_body_two_yenc_blocks(connect: Connect) -> None:
    first, second = b"first file", b"second file"
    blocks = b"".join(
        f"=ybegin line=128 size={len(p)} name=f\r\n".encode()
        + yenc_encode(p)
        + f"=yend size={len(p)} crc32={zlib.crc32(p):08x}\r\n".encode()
        for p in (first, second)
    )
    client, _ = connect(WELCOME + MODE_READER + b"222 1 <a@b>\r\n" + blocks + b".\r\n")
    assert client.body(1) == first + second


def test_body_only_blank_lines(connect: Connect) -> None:
    client, _ = connect(WELCOME + MODE_READER + b"222 1 <a@b>\r\n\r\n\r\n.\r\n")
    assert client.body(1) == b"\r\n\r\n"


def test_article_yenc_subject_plain_body(connect: Connect) -> None:
    article = b"220 1 <a@b>\r\nSubject: file yEnc (1/1)\r\n\r\nplain text\r\n.\r\n"
    client, _ = connect(WELCOME + MODE_READER + article)
    assert client.article(1)[2] == b"plain text\r\n"  # Detected from the body only


@pytest.mark.parametrize("xfeature", [False, True], ids=["no-xfeature", "xfeature"])
def test_body_message_id_with_gzip_marker_is_plain(
    connect: Connect, xfeature: bool
) -> None:
    # The status line echoes the message-id, and "=" is legal in one
    server = b"222 <COMPRESS=GZIP@x> article follows\r\nline\r\n.\r\n" + DATE
    head = WELCOME + MODE_READER + (XFEATURE_OK if xfeature else b"")
    client, _ = connect(head + server)
    if xfeature:
        client.xfeature_compress_gzip()
    assert client.body("<COMPRESS=GZIP@x>") == b"line\r\n"
    assert client.date().year == 2024


def test_gzip_marker_without_xfeature_is_plain(connect: Connect) -> None:
    server = b"222 1 <a@b> article follows COMPRESS=GZIP\r\nline\r\n.\r\n" + DATE
    client, _ = connect(WELCOME + MODE_READER + server)
    assert client.body(1) == b"line\r\n"
    assert client.date().year == 2024


@pytest.mark.parametrize(
    "status",
    [
        b"222 COMPRESS=GZIP article follows",
        b"222 <a@b> [COMPRESS=GZIP] follows",
        b"222 <COMPRESS=GZIP@x> article follows",
    ],
)
def test_gzip_marker_not_last_is_plain(connect: Connect, status: bytes) -> None:
    server = XFEATURE_OK + status + b"\r\nline\r\n.\r\n" + DATE
    client, _ = connect(WELCOME + MODE_READER + server)
    client.xfeature_compress_gzip()
    assert client.body(1) == b"line\r\n"
    assert client.date().year == 2024


@pytest.mark.parametrize("marker", [b"COMPRESS=GZIP", b"[COMPRESS=GZIP]"])
def test_gzip_marker_last_selects_gzip(connect: Connect, marker: bytes) -> None:
    payload = gzip.compress(b"line\r\n") + b".\r\n"
    status = b"222 <a@b> article follows " + marker + b"\r\n"
    server = XFEATURE_OK + status + payload + DATE
    client, _ = connect(WELCOME + MODE_READER + server)
    client.xfeature_compress_gzip()
    assert client.body(1) == b"line\r\n"
    assert client.date().year == 2024
