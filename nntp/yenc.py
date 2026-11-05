"""
Basic yEnc decoder.
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

import binascii
import re
import struct
import zlib

__all__ = ["YEnc", "check_trailer", "trailer_crc32"]


_crc32_re = re.compile(b"\\s+crc(?:32)?=([0-9a-fA-F]{8})")
_keyword_re = re.compile(rb"\s(size|part|pcrc32|crc32)=([0-9a-fA-F]+)")


def trailer_crc32(trailer: bytes) -> int | None:
    """Extract the CRC32 value from a yEnc trailer."""
    match = _crc32_re.search(trailer)
    if not match:
        return None
    buf = binascii.unhexlify(match.group(1))
    return struct.unpack(">I", buf)[0]  # type: ignore[no-any-return]


def check_trailer(trailer: bytes, size: int, crc32: int) -> str | None:
    """Check decoded data against a yEnc ``=yend`` trailer line.

    Checks ``size`` and the CRC of this part: ``pcrc32`` if given, otherwise
    ``crc32`` for a single-part post. (In a multi-part post ``crc32`` covers
    the whole file and can't be checked against one part.)

    Returns:
        None if the data matches, else a description of the mismatch.
    """
    keywords = {
        key.decode(): value.decode() for key, value in _keyword_re.findall(trailer)
    }
    if "size" in keywords and int(keywords["size"]) != size:
        return f"yEnc size mismatch: trailer {keywords['size']}, decoded {size}"
    expected = keywords.get("pcrc32")
    if expected is None and "part" not in keywords:
        expected = keywords.get("crc32")
    if expected is not None and int(expected, 16) != crc32 & 0xFFFFFFFF:
        return f"yEnc CRC mismatch: trailer {expected}, decoded {crc32:08x}"
    return None


class YEnc:
    """A basic yEnc decoder.

    Keeps track of the CRC32 value as data is decoded.
    """

    def __init__(self) -> None:
        self.crc32 = 0
        self._escape = 0

    def decode(self, buf: bytes) -> bytes:
        data = bytearray()
        for b in buf:
            if self._escape:
                b = (b - 106) & 0xFF
                self._escape = 0
            elif b == 0x3D:
                self._escape = 1
                continue
            elif b in {0x0D, 0x0A}:
                continue
            else:
                b = (b - 42) & 0xFF
            data.append(b)
        decoded = bytes(data)
        self.crc32 = zlib.crc32(decoded, self.crc32)
        return decoded
