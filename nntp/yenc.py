"""
yEnc decoding and trailer checks.
Copyright (C) 2013-2020  Byron Platt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import re
import zlib

__all__ = ["YEnc", "check_trailer", "parse_keywords", "trailer_crc32"]


_KEYWORD_RE = re.compile(rb"(\w+)=(\S*)")
# Some encoders drop leading zeros, so accept 1-8 hex digits.
_CRC32_RE = re.compile(r"[0-9a-fA-F]{1,8}")

# "=" escapes the following byte, whatever it is (including "=", CR, LF).
_ESCAPE_RE = re.compile(b"=(.)", re.DOTALL)
_PLAIN_TABLE = bytes((b - 42) & 0xFF for b in range(256))
_ESCAPED_TABLE = bytes((b - 106) & 0xFF for b in range(256))


def parse_keywords(line: bytes) -> dict[str, str]:
    """Parse the keyword=value pairs of a =ybegin, =ypart or =yend line.

    The name keyword (on =ybegin) runs to the end of the line and may contain
    spaces and "=", so it and anything after it is left out.
    """
    line = line.split(b" name=", 1)[0]
    return {
        key.decode("ascii"): value.decode("ascii", "replace")
        for key, value in _KEYWORD_RE.findall(line)
    }


def trailer_crc32(trailer: bytes, *, part: bool = False) -> int | None:
    """Extract the CRC32 value from a yEnc trailer.

    Args:
        trailer: The =yend line.
        part: Return the CRC of this part (pcrc32) rather than of the whole
            file (crc32), for multipart posts.
    """
    keywords = parse_keywords(trailer)
    if part:
        value = keywords.get("pcrc32")
    else:
        value = keywords.get("crc32", keywords.get("crc"))
    if value is None or not _CRC32_RE.fullmatch(value):
        return None
    return int(value, 16)


def check_trailer(trailer: bytes, size: int, crc32: int, *, part: bool) -> str | None:
    """Check decoded data against a =yend trailer.

    Args:
        trailer: The =yend line.
        size: Length of the decoded data.
        crc32: CRC32 of the decoded data.
        part: The data is one part of a multipart post, so it is checked
            against pcrc32 rather than the whole-file crc32.

    Returns:
        A description of the first problem, or None if the data matches. The
        size is required (yEnc 1.3). A missing CRC is not checked, but a
        malformed size, part or CRC is a problem.
    """
    keywords = parse_keywords(trailer)
    return _size_problem(keywords, size) or _crc_problem(keywords, crc32, part=part)


def _is_number(value: str) -> bool:
    return value.isascii() and value.isdigit()


def _size_problem(keywords: dict[str, str], size: int) -> str | None:
    expected = keywords.get("size")
    if expected is None:
        return "trailer has no size"
    if not _is_number(expected):
        return f"invalid size {expected!r} in trailer"
    if int(expected) != size:
        return f"decoded {size} bytes, trailer says {expected}"
    return None


def _crc_problem(keywords: dict[str, str], crc32: int, *, part: bool) -> str | None:
    number = keywords.get("part")
    if number is not None and not _is_number(number):
        return f"invalid part {number!r} in trailer"
    if part or number is not None:
        value = keywords.get("pcrc32")
    else:
        value = keywords.get("crc32", keywords.get("crc"))
    if value is None:
        return None
    if not _CRC32_RE.fullmatch(value):
        return f"invalid CRC {value!r} in trailer"
    if int(value, 16) != crc32:
        return f"CRC32 is {crc32:08x}, trailer says {int(value, 16):08x}"
    return None


class YEnc:
    """A yEnc decoder that keeps a running CRC32 of the decoded data."""

    def __init__(self) -> None:
        self.crc32 = 0
        self._escape = False

    def decode(self, buf: bytes) -> bytes:
        """Decode a chunk of yEnc data and update crc32.

        CR and LF are removed. An escape split across calls (a chunk ending in
        "=") is completed by the next call.

        Args:
            buf: yEnc data, without the =ybegin, =ypart and =yend lines.

        Returns:
            The decoded bytes.
        """
        if self._escape:
            buf = b"=" + buf
            self._escape = False

        # Alternating [plain, escaped, plain, ..., plain] segments. A plain
        # segment can only contain "=" as its final byte, in the last segment,
        # when the escaped byte is in the next buffer.
        parts = _ESCAPE_RE.split(buf)
        if parts[-1].endswith(b"="):
            parts[-1] = parts[-1][:-1]
            self._escape = True
        parts[::2] = [p.translate(_PLAIN_TABLE, b"\r\n") for p in parts[::2]]
        parts[1::2] = [p.translate(_ESCAPED_TABLE) for p in parts[1::2]]

        decoded = b"".join(parts)
        self.crc32 = zlib.crc32(decoded, self.crc32)
        return decoded
