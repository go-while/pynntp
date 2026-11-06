"""
An NNTP library - a bit more useful than the nntplib one (hopefully).
Copyright (C) 2013-2023  Byron Platt

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

import contextlib
import io
import os
import re
import socket
import ssl
import tempfile
import weakref
import zlib
from collections.abc import Iterator
from functools import cached_property
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from . import utils
from .fifo import BytesFifo
from .headerdict import HeaderDict
from .types import SSLMode
from .yenc import YEnc, check_trailer, is_keyword_line, trailer_crc32

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from datetime import datetime
    from types import TracebackType

    from typing_extensions import Self

    from .types import Newsgroup, Range

__all__ = [
    "BaseNNTPClient",
    "NNTPClient",
    "NNTPDataError",
    "NNTPError",
    "NNTPPermanentError",
    "NNTPProtocolError",
    "NNTPReplyError",
    "NNTPSyncError",
    "NNTPTemporaryError",
    "NNTPTimeoutError",
]


class NNTPError(Exception):
    """Base class for all NNTP errors."""


class NNTPTimeoutError(NNTPError, TimeoutError):
    """An NNTP socket operation timed out."""


class NNTPSyncError(NNTPError):
    """NNTP sync errors.

    Generally raised when a command is issued while another command it still
    active.
    """


class NNTPReplyError(NNTPError):
    """NNTP response status errors."""

    def __init__(self, code: int, message: str) -> None:
        """NNTP response error.

        Args:
            code: The response status code.
            message: The response message.
        """
        self.code = code
        self.message = message
        super().__init__(code, message)

    def __str__(self) -> str:
        return f"{self.code} {self.message}"


class NNTPTemporaryError(NNTPReplyError):
    """NNTP temporary errors.

    Temporary errors have response codes from 400 to 499.
    """


class NNTPPermanentError(NNTPReplyError):
    """NNTP permanent errors.

    Permanent errors have response codes from 500 to 599.
    """


# TODO: Add the status line as a parameter ?
class NNTPProtocolError(NNTPError):
    """NNTP protocol error.

    Protocol errors are raised when the response status is invalid.
    """


class NNTPDataError(NNTPError):
    """NNTP data error.

    Data errors are raised when the content of a response cannot be parsed.
    """


# Status codes that start a multi-line reply (RFC 3977 section 3.2). 211 is
# multi-line only for LISTGROUP, so it is left out.
_MULTILINE_CODES = frozenset({100, 101, 215, 220, 221, 222, 224, 225, 230, 231})


def _no_reply() -> _Reply | None:
    return None


class _Reply:
    """The lines of one multi-line reply, as returned by ``_info()``.

    The client keeps the line source itself and only a weak reference to this
    object. When nobody holds it any more (the reader finished, left its loop
    early or failed), the client reads and drops the rest of the reply before
    the next command, so the connection stays usable.
    """

    def __init__(self, client: BaseNNTPClient, source: Iterator[bytes]) -> None:
        self._client = client
        self._source = source

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> bytes:
        try:
            return next(self._source)
        except BaseException:
            # the reply is complete (StopIteration) or its source failed
            self._client._end_reply(self._source)  # noqa: SLF001
            raise

    def close(self) -> None:
        """Read and drop the rest of the reply now."""
        self._client._drain_reply(self._source)  # noqa: SLF001


class _TextReply(Iterator[str]):
    """The lines of a reply as str, as returned by ``info()``.

    Unlike a generator, its close() drops the rest of the reply at once, also
    before the first line was read.
    """

    def __init__(self, reply: _Reply, encoding: str, errors: str) -> None:
        self._reply = reply
        self._encoding = encoding
        self._errors = errors

    def __next__(self) -> str:
        return next(self._reply).decode(self._encoding, self._errors)

    def close(self) -> None:
        """Read and drop the rest of the reply now."""
        self._reply.close()


def _inflate(inflate: zlib._Decompress, data: bytes) -> bytes:
    """Decompress data, raising NNTPDataError on corrupt data."""
    try:
        return inflate.decompress(data)
    except zlib.error:
        raise NNTPDataError("Decompression failed")


def _check_yenc(begin: bytes, trailer: bytes, data: bytes, crc32: int) -> None:
    """Raise NNTPDataError if decoded yEnc data doesn't match its trailer."""
    if begin and not trailer:
        raise NNTPDataError("yEnc trailer (=yend) missing")
    if trailer:
        error = check_trailer(trailer, len(data), crc32)
        if error:
            raise NNTPDataError(error)


class BaseNNTPClient:
    """NNTP BaseNNTPClient.

    Base class for NNTP clients implements the basic command interface and
    transparently handles compressed replies.
    """

    encoding = "utf-8"
    errors = "surrogateescape"

    # COMPRESS DEFLATE (RFC 8054) state; both set by _start_compression()
    _inflater: zlib._Decompress | None = None
    _deflater: zlib._Compress | None = None

    def __init__(
        self,
        host: str,
        port: int = 119,
        username: str = "",
        password: str = "",
        *,
        timeout: int = 30,
        use_ssl: bool = False,
        ssl_mode: SSLMode = SSLMode.IMPLICIT,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        """Constructor for BasicNNTPClient.

        Connects to usenet server and enters reader mode.

        Args:
            host: Hostname for usenet server.
            port: Port for usenet server.
            username: Username for usenet account
            password: Password for usenet account
            timeout: Connection timeout
            use_ssl: Should we use SSL (TLS)
            ssl_mode: SSL (TLS) mode to use
            ssl_context: Optional TLS context; used unchanged instead of the
                default context and PYNNTP_TLS_INSECURE setting.

        Raises:
            IOError (socket.error): On error in underlying socket and/or ssl
                wrapper. See socket and ssl modules for further details.
            NNTPReplyError: On bad response code from server.
        """
        self._buffer = BytesFifo()
        self._generating = False

        self.username = username
        self.password = password
        self._tls_pending = use_ssl and ssl_mode == SSLMode.STARTTLS
        self._ssl_context = ssl_context

        # connect
        try:
            self.socket = socket.create_connection((host, port), timeout=timeout)
        except TimeoutError as exc:
            raise NNTPTimeoutError("Connection timed out") from exc
        try:
            if use_ssl and ssl_mode == SSLMode.IMPLICIT:
                self._enable_tls(host)

            code, message = self.status()
            if code not in (200, 201):
                raise NNTPReplyError(code, message)

            if use_ssl and ssl_mode == SSLMode.STARTTLS:
                self._start_tls(host)
        except BaseException:
            with contextlib.suppress(OSError):
                self.socket.close()
            raise

    def _start_tls(self, host: str) -> None:
        code, message = self.command("STARTTLS")
        if code != 382:
            raise NNTPReplyError(code, message)
        # Plaintext following 382 must not be interpreted as a TLS reply.
        self._buffer.clear()
        self._enable_tls(host)
        self._tls_pending = False

    def _enable_tls(self, host: str) -> None:
        context = self._ssl_context or ssl.create_default_context()
        insecure = os.environ.get("PYNNTP_TLS_INSECURE", "").strip().lower()
        if self._ssl_context is None and insecure in {"1", "true", "yes", "on"}:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        try:
            self.socket = context.wrap_socket(
                self.socket,
                server_hostname=host,
            )
        except TimeoutError as exc:
            raise NNTPTimeoutError("TLS negotiation timed out") from exc

    def _recv(self, size: int = 4096) -> None:
        """Reads data from the socket.

        Raises:
            NNTPTimeoutError: When the read times out. The connection is
                closed then: the late reply would be taken for the next one.
            NNTPError: When the server closed the connection.
        """
        try:
            data = self.socket.recv(size)
        except TimeoutError as exc:
            with contextlib.suppress(OSError):
                self.socket.close()
            raise NNTPTimeoutError("Reading from the server timed out") from exc
        if not data:
            raise NNTPError("Failed to read from socket")
        if self._inflater is not None:
            data = self._inflate_stream(data)
        self._buffer.write(data)

    def _inflate_stream(self, data: bytes) -> bytes:
        """Inflate data read from a COMPRESS connection.

        Corrupt data, or data after the end of the DEFLATE stream (the stream
        lasts as long as the connection), closes the connection: nothing on it
        can be read reliably any more.

        Raises:
            NNTPDataError: If the compressed stream is corrupt.
        """
        if self._inflater is None:
            return data
        try:
            data = self._inflater.decompress(data)
        except zlib.error:
            data = b""
            corrupt = True
        else:
            corrupt = bool(self._inflater.unused_data)
        if corrupt:
            with contextlib.suppress(OSError):
                self.socket.close()
            raise NNTPDataError("COMPRESS stream corrupt, connection closed")
        return data

    def _sendall(self, data: bytes) -> None:
        """Send data to the server, compressed while COMPRESS is active.

        Every write to the socket goes through here (interface I5).
        """
        if self._deflater is not None:
            data = self._deflater.compress(data) + self._deflater.flush(
                zlib.Z_SYNC_FLUSH
            )
        self.socket.sendall(data)

    def _start_compression(self) -> None:
        """Switch the connection to raw DEFLATE in both directions (RFC 8054).

        Call it right after the server's 206 reply to COMPRESS DEFLATE.
        Compression starts right after the CRLF of that reply (RFC 8054
        section 2.2.2), so bytes already read past it into the buffer are
        compressed and are inflated here.

        Raises:
            NNTPError: If compression is already active.
        """
        if self._inflater is not None:
            raise NNTPError("Compression is already active")
        self._inflater = zlib.decompressobj(-15)
        self._deflater = zlib.compressobj(
            zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15
        )
        # Anything read past the 206 line already is compressed.
        pending = self._buffer.read()
        if pending:
            self._buffer.write(self._inflate_stream(pending))

    @property
    def compressed(self) -> bool:
        """True once COMPRESS DEFLATE is active on this connection."""
        return self._inflater is not None

    def _line(self) -> Iterator[bytes]:
        """Generator that reads a line of data from the server.

        It first attempts to read from the internal buffer. If there is not
        enough data to read a line it then requests more data from the server
        and adds it to the buffer. This process repeats until a line of data
        can be read from the internal buffer.

        Yields:
            A line of data when it becomes available.
        """
        while True:
            line = self._buffer.readline()
            if not line:
                self._recv()
                continue
            yield line

    def _buf(self, length: int = 0) -> Iterator[bytes]:
        """Generator that reads a block of data from the server.

        It first attempts to read from the internal buffer. If there is not
        enough data in the internal buffer it then requests more data from the
        server and adds it to the buffer.

        Args:
            length: An optional amount of data to retrieve. A length of 0 (the
                default) will retrieve a least one buffer of data.

        Yields:
            A block of data when enough data becomes available.

        Note:
            If a length of 0 is supplied then the size of the yielded buffer
            can vary. If there is data in the internal buffer it will yield all
            of that data otherwise it will yield the the data returned by a
            recv on the socket.
        """
        while True:
            buf = self._buffer.read(length)
            if not buf:
                self._recv()
                continue
            yield buf

    def status(self) -> tuple[int, str]:
        """Reads a command response status.

        If there is no response message then the returned status message will
        be an empty string.

        Raises:
            NNTPError: If data is required to be read from the socket and
                fails.
            NNTPProtocolError: If the status line can't be parsed.
            NNTPTemporaryError: For status code 400-499
            NNTPPermanentError: For status code 500-599

        Returns:
            A tuple of status code and status message.
        """
        line = next(self._line()).rstrip()
        parts = line.split(None, 1)
        text = line.decode(self.encoding, self.errors)

        try:
            code, data = int(parts[0]), b""
        except (IndexError, ValueError):
            raise NNTPProtocolError(f"Invalid status line: {text!r}")

        if code < 100 or code >= 600:
            raise NNTPProtocolError(f"Invalid status line: {text!r}")

        if len(parts) > 1:
            data = parts[1]

        message = data.decode(self.encoding, self.errors)

        if 400 <= code <= 499:
            raise NNTPTemporaryError(code, message)

        if 500 <= code <= 599:
            raise NNTPPermanentError(code, message)

        return code, message

    def _info_plain(self) -> Iterator[bytes]:
        """Generator for the lines of an info (textual) response.

        When a terminating line (line containing single period) is received the
        generator exits.

        If there is a line beginning with an 'escaped' period then the extra
        period is trimmed.

        Yields:
            A line of the info response.

        Raises:
            NNTPError: If data is required to be read from the socket and
                fails.
        """
        for line in self._line():
            if line == b".\r\n":
                break
            if line.startswith(b"."):
                line = line[1:]
            yield line

    def _info_gzip(self) -> Iterator[bytes]:
        """Generator for the lines of a compressed info (textual) response.

        Compressed responses are an extension to the NNTP protocol supported by
        some usenet servers to reduce the bandwidth of heavily used range style
        commands that can return large amounts of textual data.

        This function handles gzip compressed responses that have the
        terminating line inside or outside the compressed data. From experience
        if the 'XFEATURE COMPRESS GZIP' command causes the terminating
        '.\\r\\n' to follow the compressed data and 'XFEATURE COMPRESS GZIP
        TERMINATOR' causes the terminator to be the last part of the compressed
        data (i.e the reply the gzipped version of the original reply -
        terminating line included)

        This function will produce that same output as the _info_plain()
        function. In other words it takes care of decompression.

        Yields:
            A line of the info response.

        Raises:
            NNTPError: If data is required to be read from the socket and
                fails.
            NNTPDataError: If decompression fails.
        """
        inflate = zlib.decompressobj(15 + 32)

        done, buf = False, BytesFifo()
        while not done:
            data = next(self._buf())
            if inflate.eof:
                # the terminator follows the compressed data
                buf.write(data)
            else:
                buf.write(self._inflate_or_close(inflate, data))
                if inflate.eof:
                    # whatever came after the end of the gzip stream, once
                    buf.write(inflate.unused_data)
            for line in buf:
                if line == b".\r\n":
                    done = True
                    break
                if line.startswith(b"."):
                    line = line[1:]
                yield line

        if inflate.eof:
            # raw bytes after the terminator belong to the next reply
            rest = buf.read()
        else:
            # The terminator was inside the compressed data: read the rest of
            # the gzip stream (at least its trailer) so that it can't be taken
            # for the next reply. Whatever follows the stream is that reply.
            buf.clear()
            while not inflate.eof:
                self._inflate_or_close(inflate, next(self._buf()))
            rest = inflate.unused_data
        if rest:
            buffer = BytesFifo()
            buffer.write(rest)
            buffer.write(self._buffer.read())
            self._buffer = buffer

    def _inflate_or_close(self, inflate: zlib._Decompress, data: bytes) -> bytes:
        """Decompress part of a gzip reply; close the connection if corrupt.

        The end of a corrupt compressed reply can't be found, so the
        connection can't be used for further commands.
        """
        try:
            return _inflate(inflate, data)
        except NNTPDataError:
            self.socket.close()
            raise NNTPDataError("Decompression failed, connection closed")

    def _info_yenczlib(self) -> Iterator[bytes]:
        """Generator for the lines of a compressed info (textual) response.

        Compressed responses are an extension to the NNTP protocol supported by
        some usenet servers to reduce the bandwidth of heavily used range style
        commands that can return large amounts of textual data. The server
        returns that same data as it would for the uncompressed versions of the
        command the difference being that the data is zlib deflated and then
        yEnc encoded.

        This function will produce that same output as the info()
        function. In other words it takes care of decoding and decompression.

        Yields:
            A line of the info response.

        Raises:
            NNTPError: If data is required to be read from the socket and
                fails.
            NNTPDataError: When there is an error parsing the yEnc header or
                trailer, if the CRC check fails or decompressing data fails.
        """

        decoder = YEnc()
        inflate = zlib.decompressobj(-15)

        # one iterator for the whole reply: header, data and trailer
        lines = self._info_plain()
        try:
            # header
            header = next(lines, b"")
            if not header.startswith(b"=ybegin"):
                raise NNTPDataError("Bad yEnc header")

            # data
            buf, trailer = BytesFifo(), b""
            for line in lines:
                if line.startswith(b"=yend"):
                    trailer = line
                    continue
                data = _inflate(inflate, decoder.decode(line))
                if not data:
                    continue
                buf.write(data)
                yield from buf
        except NNTPDataError:
            for _ in lines:  # read the rest of the reply
                pass
            raise

        # trailer
        if not trailer:
            raise NNTPDataError("Missing yEnc trailer")

        # expected crc32
        crc32 = trailer_crc32(trailer)
        if crc32 is None:
            raise NNTPDataError("Bad yEnc trailer")

        # check crc32
        if crc32 != decoder.crc32:
            raise NNTPDataError("Bad yEnc CRC")

    @property
    def _generating(self) -> bool:
        """True while a multi-line reply is still being read.

        A reply that nobody holds any more is read to its end and dropped
        here, so that the next command can be sent.
        """
        if self._reply_source is None:
            return False
        if self._reply_handle() is not None:
            return True
        self._drain_reply(self._reply_source)
        return False

    @_generating.setter
    def _generating(self, value: bool) -> None:
        # only "no reply in progress" can be set (by __init__)
        if value:
            msg = "_generating can only be set to False"
            raise ValueError(msg)
        self._reply_source: Iterator[bytes] | None = None
        self._reply_handle: Callable[[], _Reply | None] = _no_reply

    def _end_reply(self, source: Iterator[bytes]) -> None:
        """Mark the reply read by ``source`` as complete."""
        if self._reply_source is source:
            self._generating = False

    def _drain_reply(self, source: Iterator[bytes]) -> None:
        """Read and drop the rest of the reply read by ``source``."""
        if self._reply_source is not source:
            return
        try:
            for _ in source:
                pass
        except NNTPDataError:
            # Bad data (e.g. a yEnc CRC) after the reply was read to its end
            # is not the next command's business. If the end couldn't be
            # found, the connection was closed: say so.
            if self.socket.fileno() == -1:
                raise
        finally:
            self._end_reply(source)

    def _unexpected(self, code: int, message: str) -> NNTPReplyError:
        """Return the error for an unexpected success code of a command.

        If the code starts a multi-line reply, the reply is read and dropped
        first, so the connection stays usable. Use: ``raise
        self._unexpected(code, message)``.
        """
        if code in _MULTILINE_CODES:
            self._info(code, message).close()
        return NNTPReplyError(code, message)

    def _info(self, code: int, message: str, yz: bool = False) -> _Reply:
        """Dispatcher for the info generators.

        Determines which _info_*() generator should be used based on the
        supplied parameters.

        Args:
            code: The status code for the command response.
            message: The status message for the command response.
            yz: Use yenzlib decompression. Useful for xz* commands.

        Returns:
            An iterator over the lines of the info response as bytes. Its
            close() method drops the rest of the reply.

        Raises:
            NNTPSyncError: If another reply is still being read.
        """
        if self._generating:
            raise NNTPSyncError("Another reply is still being read")
        source: Iterator[bytes]
        if "COMPRESS=GZIP" in message:
            source = self._info_gzip()
        else:
            source = self._info_yenczlib() if yz else self._info_plain()
        reply = _Reply(self, source)
        self._reply_source = source
        self._reply_handle = weakref.ref(reply)
        return reply

    def info(self, code: int, message: str, yz: bool = False) -> Iterator[str]:
        """Dispatcher for the info generators.

        Determines which _info_*() generator should be used based on the
        supplied parameters.

        Args:
            code: The status code for the command response.
            message: The status message for the command response.
            yz: Use yenzlib decompression. Useful for xz* commands.

        Returns:
            An iterator over the lines of the info response as strings. The
            reply counts as being read from the moment info() returns until
            the iterator is exhausted, closed with its close() method, or
            dropped.
        """
        return _TextReply(self._info(code, message, yz), self.encoding, self.errors)

    def _decode(self, lines: Iterable[bytes]) -> Iterator[str]:
        """Decode lines of bytes to str."""
        for line in lines:
            yield line.decode(self.encoding, self.errors)

    def command(self, verb: str, args: str | None = None) -> tuple[int, str]:
        """Call a command on the server.

        If the user has not authenticated then authentication will be done
        as part of calling the command on the server.

        For commands that don't return a status message the status message
        will default to an empty string.

        Args:
            verb: The verb of the command to call.
            args: The arguments of the command as a string (default None).

        Returns:
            A tuple of status code (as an integer) and status message.

        Raises:
            ValueError: If the verb or arguments contain CR, LF or NUL.

        Note:
            You can run raw commands by supplying the full command (including
            args) in the verb.

        CR, LF and NUL are rejected in both the verb and arguments.
        """
        if self.socket.fileno() == -1:
            raise NNTPError("Connection is closed")
        if self._generating:
            raise NNTPSyncError("Command issued while a generator is active")

        try:
            return self._command_once(verb, args)
        except NNTPTemporaryError as e:
            command = f"{verb} {args or ''}".upper().split()
            if (
                e.code != 480
                or self._tls_pending
                or self.compressed
                or not self.username
                or command[:2] == ["MODE", "READER"]
                or command[:1] == ["AUTHINFO"]
            ):
                raise
            self.login()
            return self._command_once(verb, args)

    def _command_once(self, verb: str, args: str | None = None) -> tuple[int, str]:
        """Send one command without automatic authentication or retries."""
        self._validate_command(verb, args)
        parts = f"{verb} {args or ''}".upper().split()
        if self.compressed and (
            parts[:1] in (["AUTHINFO"], ["STARTTLS"], ["COMPRESS"])
            or parts[:2] == ["MODE", "READER"]
        ):
            raise NNTPError("Command unavailable after compression")
        if (
            (
                parts[:1] in (["COMPRESS"], ["STARTTLS"])
                or parts[:2] == ["MODE", "READER"]
            )
            and isinstance(self.socket, ssl.SSLSocket)
            and self.socket.compression() is not None
        ):
            raise NNTPError("Command unavailable while TLS compression is active")
        if self.socket.fileno() == -1:
            raise NNTPError("Connection is closed")
        cmd = f"{verb} {args}\r\n" if args else f"{verb}\r\n"
        try:
            self._sendall(cmd.encode(self.encoding))
        except TimeoutError as exc:
            # A partial command may have reached the server; don't reuse it.
            with contextlib.suppress(OSError):
                self.socket.close()
            raise NNTPTimeoutError("Sending command timed out") from exc
        return self.status()

    @staticmethod
    def _validate_command(verb: str, args: str | None = None) -> None:
        if any(char in value for value in (verb, args or "") for char in "\r\n\0"):
            raise ValueError(
                "Command verb and arguments must not contain CR, LF or NUL"
            )

    def login(self, username: str | None = None, password: str | None = None) -> None:
        """Authenticate using AUTHINFO USER/PASS, defaulting to stored credentials.

        Authentication errors propagate without retries. A username is required,
        and credentials are never sent while a requested STARTTLS is pending.
        If the server requests a password, an empty password raises NNTPError.
        """
        if self.compressed:
            raise NNTPError("Cannot authenticate after compression")
        if self._generating:
            raise NNTPSyncError("Command issued while a generator is active")
        if self._tls_pending:
            raise NNTPError("Cannot authenticate before STARTTLS")
        username = self.username if username is None else username
        password = self.password if password is None else password
        if not username:
            raise NNTPError("A username is required for authentication")
        # Validate both fields before sending AUTHINFO USER.
        self._validate_command("AUTHINFO USER", username)
        self._validate_command("AUTHINFO PASS", password)
        code, message = self._command_once("AUTHINFO USER", username)
        if code == 381:
            if not password:
                raise NNTPError("A password is required for authentication")
            code, message = self._command_once("AUTHINFO PASS", password)
        if code != 281:
            raise NNTPReplyError(code, message)
        self.username, self.password = username, password

    def compress(self) -> None:
        """Enable RFC 8054 DEFLATE compression for this connection.

        Authenticate and negotiate TLS before calling this method: after
        compression, AUTHINFO, STARTTLS and MODE READER are prohibited.
        Compression can weaken TLS confidentiality for sensitive data.
        """
        code, message = self.command("COMPRESS", "DEFLATE")
        if code != 206:
            raise self._unexpected(code, message)
        self._start_compression()

    def close(self) -> None:
        """Closes the connection at the client.

        Once this method has been called, no other methods of the NNTPClient
        object should be called.
        """
        self.socket.close()


_CommandValue = TypeVar("_CommandValue")


class _CommandReply(Generic[_CommandValue]):
    """A streamed C-command parser owning an already-registered raw reply.

    No client cache owns this wrapper. Dropping it releases the raw handle so
    the next command drains; explicit close and parser failures drain at once,
    even when this wrapper or its exception traceback is still held.
    """

    def __init__(
        self,
        reply: _Reply,
        parse: Callable[[str], _CommandValue],
        encoding: str,
        errors: str,
    ) -> None:
        self._reply: _Reply | None = reply
        self._parse = parse
        self._encoding = encoding
        self._errors = errors

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> _CommandValue:
        if self._reply is None:
            raise StopIteration
        try:
            line = next(self._reply).decode(self._encoding, self._errors)
            return self._parse(line)
        except StopIteration:
            self._reply = None
            raise
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Drain the reply and release it, including before first iteration."""
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.close()


class NNTPClient(BaseNNTPClient):
    """NNTP NNTPClient.

    Implements many of the commands that are commonly used by current usenet
    servers. Including handling commands that use compressed responses.

    Implements generators for commands for which generators are likely to
    yield (bad pun warning) performance gains. These gains will be in the form
    of lower memory consumption and the added ability to process and receive
    data in parallel. If you are using commands that can take a range as an
    argument or can return large amounts of data there should be a _gen()
    version of the command and it should be used in preference to the standard
    version.

    Note: All commands can raise the following exceptions:
            NNTPError
            NNTPProtocolError
            NNTPPermanentError
            NNTPReplyError
            IOError (socket.error)

    Note: All commands that use compressed responses can also raise an
        NNTPDataError.
    """

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int = 119,
        username: str = "",
        password: str = "",
        *,
        timeout: int = 30,
        use_ssl: bool = False,
        ssl_mode: SSLMode = SSLMode.IMPLICIT,
        reader: bool = True,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        """Constructor for NNTP NNTPClient.

        Connects to usenet server.

        Args:
            host: Hostname for usenet server.
            port: Port for usenet server.
            username: Username for usenet account
            password: Password for usenet account
            timeout: Connection timeout
            use_ssl: Should we use ssl
            ssl_mode: SSL mode to use
            reader: Use reader mode
            ssl_context: Optional TLS context, used unchanged.

        Note:
            With STARTTLS, MODE READER is attempted before upgrading. If it
            requires authentication or encryption (480/483), the upgrade
            proceeds without retrying MODE READER or sending credentials in
            plaintext.

        Raises:
            socket.error: On error in underlying socket and/or ssl wrapper. See
                socket and ssl modules for further details.
            NNTPReplyError: On bad response code from server.
        """
        starttls = use_ssl and ssl_mode == SSLMode.STARTTLS
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            use_ssl=use_ssl and not starttls,
            ssl_mode=ssl_mode,
            ssl_context=ssl_context,
        )
        try:
            self._tls_pending = starttls
            if reader:
                try:
                    self.mode_reader()
                except NNTPTemporaryError as exc:
                    if not starttls or exc.code not in (480, 483):
                        raise
            if starttls:
                self._start_tls(host)
        except BaseException:
            with contextlib.suppress(OSError):
                self.socket.close()
            raise

    def __enter__(self) -> Self:
        """Support for the 'with' context manager statement."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Support for the 'with' context manager statement."""
        if exc_type is not None:
            # Do not replace the exception raised by the user's block.
            with contextlib.suppress(OSError):
                self.close()
        else:
            try:
                # Shutdown errors must not turn a successful block into failure.
                with contextlib.suppress(NNTPError, OSError):
                    if not self._generating:
                        self.quit()
            finally:
                with contextlib.suppress(OSError):
                    self.close()
        return False

    # session administration commands
    def capabilities(self, keyword: str | None = None) -> Iterator[str]:
        """CAPABILITIES command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Determines the capabilities of the server.

        Although RFC3977 states that this is a required command for servers to
        implement not all servers do, so expect that NNTPPermanentError may be
        raised when this command is issued.

        See <http://tools.ietf.org/html/rfc3977#section-5.2>

        Args:
            keyword: Passed directly to the server, however, this is unused by
                the server according to RFC3977.

        Yields:
            Each of the capabilities supported by the server. The VERSION
            capability is the first capability to be yielded.
        """
        args = keyword

        code, message = self.command("CAPABILITIES", args)
        if code != 101:
            raise self._unexpected(code, message)

        return self._command_reply(code, message, str.strip)

    def mode_reader(self) -> bool:
        """MODE READER command.

        Instructs a mode-switching server to switch modes.

        See <http://tools.ietf.org/html/rfc3977#section-5.3>

        Returns:
            Boolean value indicating whether posting is allowed or not. If
            authentication was required, posting permission is unknown and
            False is returned without retrying MODE READER after authentication.
        """
        try:
            code, message = self.command("MODE READER")
        except NNTPTemporaryError as exc:
            if exc.code != 480 or self._tls_pending or not self.username:
                raise
            self.login()
            return False
        if code not in (200, 201):
            raise NNTPReplyError(code, message)

        return code == 200

    def quit(self) -> None:
        """QUIT command.

        Tells the server to close the connection. After the server acknowledges
        the request to quit the connection is closed both at the server and
        client. Only useful for graceful shutdown. The socket is also closed if
        QUIT fails. An active generator prevents QUIT and raises NNTPSyncError;
        use close() instead when a reply is still being read.

        Once this method has been called, no other methods of the NNTPClient
        object should be called.

        See <http://tools.ietf.org/html/rfc3977#section-5.4>
        """
        if self.socket.fileno() == -1:
            return
        try:
            code, message = self.command("QUIT")
            if code != 205:
                raise NNTPReplyError(code, message)
        finally:
            self.close()

    # information commands
    def date(self) -> datetime:
        """DATE command.

        Coordinated Universal time from the perspective of the usenet server.
        It can be used to provide information that might be useful when using
        the NEWNEWS command.

        See <http://tools.ietf.org/html/rfc3977#section-7.1>

        Returns:
            The UTC time according to the server as a datetime object.

        Raises:
            NNTPDataError: If the timestamp can't be parsed.
        """
        code, message = self.command("DATE")
        if code != 111:
            raise self._unexpected(code, message)

        try:
            return utils.parse_date(message)
        except ValueError as exc:
            raise NNTPDataError(f'Invalid DATE response "{message}"') from exc

    def help(self) -> str:
        """HELP command.

        Provides a short summary of commands that are understood by the usenet
        server.

        See <http://tools.ietf.org/html/rfc3977#section-7.2>

        Returns:
            The help text from the server.
        """
        code, message = self.command("HELP")
        if code != 100:
            raise self._unexpected(code, message)

        return "".join(self.info(code, message))

    def _command_reply(
        self,
        code: int,
        message: str,
        parse: Callable[[str], _CommandValue],
        *,
        yz: bool = False,
    ) -> Iterator[_CommandValue]:
        """Register a reply now, returning an owning streaming parser."""
        return _CommandReply(
            self._info(code, message, yz), parse, self.encoding, self.errors
        )

    @staticmethod
    def _parse_newsgroup(line: str) -> Newsgroup:
        try:
            return utils.parse_newsgroup(line)
        except ValueError as exc:
            raise NNTPDataError(str(exc)) from exc

    def newgroups(self, timestamp: datetime) -> Iterator[Newsgroup]:
        """NEWGROUPS command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Retrieves a list of newsgroups created on the server since the
        specified timestamp.

        See <http://tools.ietf.org/html/rfc3977#section-7.3>

        Args:
            timestamp: Datetime object giving 'created since'

        Yields:
            A 4-tuple containing the name, low water mark, high water mark, and
            status for the newsgroup, for each newsgroup.

        Note: If the datetime object supplied as the timestamp is naive (tzinfo
            is None) then it is assumed to be given as GMT.
        """
        args = utils.unparse_timestamp(timestamp)

        code, message = self.command("NEWGROUPS", args)
        if code != 231:
            raise self._unexpected(code, message)

        return self._command_reply(code, message, self._parse_newsgroup)

    def newnews(self, pattern: str, timestamp: datetime) -> Iterator[str]:
        """NEWNEWS command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Retrieves a list of message-ids for articles created since the
        specified timestamp for newsgroups with names that match the given
        pattern.

        See <http://tools.ietf.org/html/rfc3977#section-7.4>

        Args:
            pattern: Glob matching newsgroups of interest.
            timestamp: Datetime object giving 'created since'

        Yields:
            A message-id as string, for each article.

        Note: If the datetime object supplied as the timestamp is naive (tzinfo
            is None) then it is assumed to be given as GMT. If tzinfo is set
            then it will be converted to GMT by this function.
        """
        args = f"{pattern} {utils.unparse_timestamp(timestamp)}"

        code, message = self.command("NEWNEWS", args)
        if code != 230:
            raise self._unexpected(code, message)

        return self._command_reply(code, message, str.strip)

    # list commands
    def list(
        self,
        keyword: str | None = None,
        args: str | None = None,
        *,
        success: Iterable[int] = (215,),
    ) -> Iterator[str]:
        """LIST command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        General purpose list command. allows the server to provide blocks of
        information to the client. The keyword specifies the type of list, if no
        keyword is provided, it defaults to ACTIVE.

        See <http://tools.ietf.org/html/rfc3977#section-7.6.1>

        Args:
            keyword: Information requested.
            args: Keyword specific arguments.

        Yields:
            A line of the list response.
        """
        if keyword:
            keyword = keyword.upper()

        cmd = f"LIST {keyword}" if keyword else "LIST"

        code, message = self.command(cmd, args)
        if code not in success:
            raise self._unexpected(code, message)

        return self._command_reply(code, message, lambda line: line)

    def list_active(self, pattern: str | None = None) -> Iterator[Newsgroup]:
        """LIST ACTIVE command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Retrieves a list of active newsgroups that match the specified pattern.

        See <http://tools.ietf.org/html/rfc3977#section-7.6.3>

        Args:
            pattern: Glob matching newsgroups of interest.

        Yields:
            A 4-tuple containing the name, low water mark, high water mark,
            and status for the newsgroup, for each newsgroup.
        """
        code, message = self.command("LIST ACTIVE", pattern)
        if code != 215:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, self._parse_newsgroup)

    def list_active_times(self) -> Iterator[tuple[str, datetime, str]]:
        """LIST ACTIVE TIMES command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Retrieves a list of newsgroups including the creation time and who
        created them.

        See <http://tools.ietf.org/html/rfc3977#section-7.6.4>

        Yields:
            A 3-tuple containing the name, creation date as a datetime object
            and creator as a string for the newsgroup for each newsgroup.
        """

        def parse(line: str) -> tuple[str, datetime, str]:
            parts = line.split()
            try:
                name = parts[0]
                timestamp = utils.parse_epoch(parts[1])
                creator = parts[2]
            except (IndexError, ValueError):
                raise NNTPDataError("Invalid LIST ACTIVE.TIMES")
            return name, timestamp, creator

        code, message = self.command("LIST ACTIVE.TIMES")
        if code != 215:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, parse)

    def list_headers(
        self, variant: Literal["MSGID", "RANGE"] | None = None
    ) -> Iterator[str]:
        """LIST HEADERS command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Returns a list of fields that may be retrieved using the HDR command.

        See <https://tools.ietf.org/html/rfc3977#section-8.6>

        Args:
            variant: The string 'MSGID' or 'RANGE' or None (the default).
                Different variants of the HDR request may return a different
                fields.

        Yields:
            The field name for each of the fields.
        """
        code, message = self.command("LIST HEADERS", variant)
        if code != 215:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, str.strip)

    def list_newsgroups(
        self,
        pattern: str | None = None,
    ) -> Iterator[tuple[str, str]]:
        """LIST NEWSGROUPS command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Retrieves a list of newsgroups including the name and a short
        description.

        This is not necessarily a complete list of available groups. RFC 3977
        permits the server to omit groups without descriptions; INN uses its
        newsgroups description file, so a newly created group may be absent
        until its description is added there. This is server data, not a
        client-side cache (upstream issue #95). Use list_active(pattern) to
        discover available groups and their water marks instead.

        See <http://tools.ietf.org/html/rfc3977#section-7.6.6>

        Args:
            pattern: Glob matching newsgroups of interest.

        Yields:
            A tuple containing the name, and description for the newsgroup, for
            each newsgroup that matches the pattern.
        """

        def parse(line: str) -> tuple[str, str]:
            parts = line.strip().split(None, 1)
            name, description = parts[0], ""
            if len(parts) > 1:
                description = parts[1]
            return name, description

        code, message = self.command("LIST NEWSGROUPS", pattern)
        if code != 215:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, parse)

    def list_overview_fmt(self) -> Iterator[tuple[str, bool]]:
        """LIST OVERVIEW.FMT command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Returns a description of the fields in the database for which it is
        consistent.

        See <https://tools.ietf.org/html/rfc3977#section-8.4>

        Yields:
            A 2-tuple of the name of the field and a boolean indicating whether
            the the field name is included in the field data, for each field in
            the database which is consistent, fields are yielded in order.
        """

        def parse(line: str) -> tuple[str, bool]:
            try:
                name, suffix = line.rstrip().split(":")
            except ValueError:
                raise NNTPDataError("Invalid LIST OVERVIEW.FMT")
            if suffix and not name:
                name, suffix = suffix, name
            if suffix and suffix.casefold() != "full":
                raise NNTPDataError("Invalid LIST OVERVIEW.FMT")
            return name, suffix.casefold() == "full"

        code, message = self.command("LIST OVERVIEW.FMT")
        if code != 215:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, parse)

    def list_extensions(self) -> Iterator[str]:
        """LIST EXTENSIONS command.

        Sends immediately; the returned iterator has the ownership rules of list().

        Allows a client to determine which extensions are supported by the
        server at any given time.

        See <https://tools.ietf.org/html/draft-ietf-nntpext-base-20#section-5.3>

        This obsolete draft command expects legacy status 202. Servers such as
        INN may reject it with 501; that NNTPPermanentError is propagated. Use
        capabilities() for RFC 3977 capability discovery instead.

        Yields:
            The name of the extension of each of the available extensions.
        """
        code, message = self.command("LIST EXTENSIONS")
        if code != 202:
            raise self._unexpected(code, message)
        return self._command_reply(code, message, str.strip)

    def group(self, name: str) -> tuple[int, int, int, str]:
        """GROUP command.

        Selects a newsgroup as the currently selected newsgroup and returns
        summary information about it.

        See <https://tools.ietf.org/html/rfc3977#section-6.1.1>

        Args:
            name: The group name.

        Returns:
            A 4-tuple of the estimated total articles in the group, the
            articles numbers of the first and last article and the group name.

        Raises:
            NNTPReplyError: If no such newsgroup exists.
        """
        args = name

        code, message = self.command("GROUP", args)
        if code != 211:
            raise self._unexpected(code, message)

        parts = message.split(None, 4)
        try:
            total = int(parts[0])
            first = int(parts[1])
            last = int(parts[2])
            group = parts[3]
        except (IndexError, ValueError):
            raise NNTPDataError(f'Invalid GROUP status "{message}"')

        return total, first, last, group

    def listgroup(
        self, name: str | None = None, range: Range | None = None
    ) -> Iterator[int]:
        """LISTGROUP command: select a group and yield its article numbers.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        With no name, use the currently selected group. A range requires an
        explicit group name because the wire grammar is ``group [range]``.
        The 211 status metadata is validated but only article numbers are
        yielded. An empty group or range yields no numbers.

        See <https://www.rfc-editor.org/rfc/rfc3977#section-6.1.2>.

        Raises:
            ValueError: If a range is supplied without a group name.
            NNTPDataError: If the status or an article number is malformed.
        """
        args = name
        if range is not None:
            if not name:
                raise ValueError("LISTGROUP range requires a group name")
            args = f"{name} {utils.unparse_range(range)}"
        code, message = self.command("LISTGROUP", args)
        if code != 211:
            raise self._unexpected(code, message)
        try:
            parts = message.split()
            if len(parts) < 4 or any(int(part) < 0 for part in parts[:3]):
                raise ValueError("Invalid group status")
        except ValueError as exc:
            self._info(code, message).close()
            raise NNTPDataError(f'Invalid LISTGROUP status "{message}"') from exc

        def parse(line: str) -> int:
            try:
                number = int(line)
                if number <= 0:
                    raise ValueError("Article numbers must be positive")
            except ValueError as exc:
                raise NNTPDataError("Invalid LISTGROUP article number") from exc
            return number

        return self._command_reply(code, message, parse)

    def next(self) -> tuple[int, str]:
        """NEXT command.

        Sets the current article number to the next article in the current
        newsgroup.

        See <https://tools.ietf.org/html/rfc3977#section-6.1.4>

        Returns:
            A 2-tuple of the article number and message id.

        Raises:
            NNTPReplyError: If no such article exists or the currently selected
                newsgroup is invalid.
        """
        code, message = self.command("NEXT")
        if code != 223:
            raise self._unexpected(code, message)

        parts = message.split(None, 3)
        try:
            article = int(parts[0])
            msgid = parts[1]
        except (IndexError, ValueError):
            raise NNTPDataError("Invalid NEXT status")

        return article, msgid

    def last(self) -> tuple[int, str]:
        """LAST command.

        Sets the current article number to the previous article in the current
        newsgroup.

        See <https://tools.ietf.org/html/rfc3977#section-6.1.3>

        Returns:
            A 2-tuple of the article number and message id.

        Raises:
            NNTPReplyError: If no such article exists or the currently selected
                newsgroup is invalid.
        """
        code, message = self.command("LAST")
        if code != 223:
            raise self._unexpected(code, message)

        parts = message.split(None, 3)
        try:
            article = int(parts[0])
            msgid = parts[1]
        except (IndexError, ValueError):
            raise NNTPDataError("Invalid LAST status")

        return article, msgid

    def stat(self, msgid_article: str | int | None = None) -> tuple[int, str]:
        """STAT command: return an article's number and Message-ID, not its text.

        The selector is a Message-ID, an article number, or None for the
        current article. By Message-ID, the server may return number 0 or
        the article's number in the currently selected group.

        See <https://www.rfc-editor.org/rfc/rfc3977#section-6.2.4>.

        Raises:
            NNTPDataError: If the successful response cannot be parsed.
        """
        args = str(msgid_article) if msgid_article is not None else None
        code, message = self.command("STAT", args)
        if code != 223:
            raise self._unexpected(code, message)
        try:
            parts = message.split(None, 2)
            number = int(parts[0])
            message_id = parts[1]
            if number < 0 or re.fullmatch(r"<[^<>\s]+>", message_id) is None:
                raise ValueError("Invalid article number or Message-ID")
        except (IndexError, ValueError) as exc:
            raise NNTPDataError(f'Invalid STAT status "{message}"') from exc
        return number, message_id

    def _parse_headers(self, lines: Iterator[bytes]) -> HeaderDict:
        """Parse the headers of an ARTICLE or HEAD reply.

        Raises:
            NNTPDataError: If the headers can't be parsed.
        """
        try:
            return utils.parse_headers(self._decode(lines))
        except ValueError as e:
            raise NNTPDataError(f"Invalid article headers: {e}") from e

    def _body(self, lines: Iterator[bytes], decode: bool | None = None) -> bytes:
        """Read an article body; decode it if it is yEnc.

        Raises:
            NNTPDataError: If yEnc data doesn't match the size or CRC in its
                ``=yend`` trailer. The reply has been read to its end then.
        """
        decoder = YEnc()

        # read the body
        body: list[bytes] = []
        begin = trailer = b""
        for line in lines:
            # detect yenc
            if decode is None:
                if is_keyword_line(line, b"=ybegin"):
                    decode = True
                    del body[:]
                elif line != b"\r\n":
                    decode = False

            # decode yenc
            if decode:
                if trailer:
                    continue  # text after =yend is not part of the data
                if is_keyword_line(line, b"=ybegin"):
                    begin = line
                    continue
                if is_keyword_line(line, b"=yend"):
                    trailer = line
                    continue
                if is_keyword_line(line, b"=ypart"):
                    continue
                line = decoder.decode(line)

            body.append(line)

        data = b"".join(body)
        _check_yenc(begin, trailer, data, decoder.crc32)
        return data

    def article(
        self,
        msgid_article: str | int | None = None,
        decode: bool | None = None,
    ) -> tuple[int, HeaderDict, bytes]:
        """ARTICLE command.

        Selects an article according to the arguments and presents the entire
        article (that is, the headers, an empty line, and the body, in that
        order) to the client.

        See <https://tools.ietf.org/html/rfc3977#section-6.2.1>

        Args:
            msgid_article: A message-id as a string, or an article number as an
                integer. A msgid_article of None (the default) uses the current
                article.
            decode: Force yenc decoding to be enabled or disabled. A value of
                None (the default) attempts to determine this automatically.

        Returns:
            A 3-tuple of the article number, the article headers, and the
            article body. The headers are decoded to unicode, where as the body
            is returned as bytes.

        Raises:
            NNTPReplyError: If no such article exists.
        """
        args = None
        if msgid_article is not None:
            args = str(msgid_article)

        code, message = self.command("ARTICLE", args)
        if code != 220:
            raise self._unexpected(code, message)

        parts = message.split(None, 1)

        try:
            articleno = int(parts[0])
        except ValueError:
            raise NNTPProtocolError(message)

        # headers and body come from one reply, so read both from one iterator
        lines = self._info(code, message)
        try:
            headers = self._parse_headers(lines)

            if decode is None and "yEnc" in headers.get("subject", ""):
                decode = True

            body = self._body(lines, decode=decode)
        finally:
            lines.close()

        return articleno, headers, body

    def head(self, msgid_article: str | int | None = None) -> HeaderDict:
        """HEAD command.

        Identical to the ARTICLE command except that only the headers are
        presented.

        See <https://tools.ietf.org/html/rfc3977#section-6.2.2>

        Args:
            msgid_article: A message-id as a string, or an article number as an
                integer. A msgid_article of None (the default) uses the current
                article.

        Returns:
            The article headers.

        Raises:
            NNTPReplyError: If no such article exists.
        """
        args = None
        if msgid_article is not None:
            args = str(msgid_article)

        code, message = self.command("HEAD", args)
        if code != 221:
            raise self._unexpected(code, message)

        lines = self._info(code, message)
        try:
            return self._parse_headers(lines)
        finally:
            lines.close()

    def body(
        self,
        msgid_article: str | int | None = None,
        decode: bool | None = None,
    ) -> bytes:
        """BODY command.

        Identical to the ARTICLE command except that only the body is
        presented.

        See <https://tools.ietf.org/html/rfc3977#section-6.2.3>

        Args:
            msgid_article: A message-id as a string, or an article number as an
                integer. A msgid_article of None (the default) uses the current
                article.
            decode: Force yenc decoding to be enabled or disabled. A value of
                None (the default) attempts to determine this automatically.

        Returns:
            The article body.

        Raises:
            NNTPReplyError: If no such article exists.
        """
        args = None
        if msgid_article is not None:
            args = str(msgid_article)

        code, message = self.command("BODY", args)
        if code != 222:
            raise self._unexpected(code, message)

        lines = self._info(code, message)
        try:
            return self._body(lines, decode=decode)
        finally:
            lines.close()

    def _hdr(
        self,
        header: str,
        msgid_range: str | Range | None = None,
        verb: str = "HDR",
    ) -> Iterator[tuple[int, str]]:
        args = header
        if msgid_range is not None:
            args += " " + utils.unparse_msgid_range(msgid_range)
        requested_id = (
            msgid_range
            if verb in ("XHDR", "XZHDR")
            and isinstance(msgid_range, str)
            and re.fullmatch(r"<[^<>\s]+>", msgid_range)
            else None
        )

        code, message = self.command(verb, args)
        success = 225 if verb == "HDR" else 221
        if code != success:
            raise self._unexpected(code, message)

        def parse(line: str) -> tuple[int, str]:
            parts = line.rstrip("\r\n").split(None, 1)
            try:
                articleno = 0 if parts[0] == requested_id else int(parts[0])
                value = parts[1] if len(parts) > 1 else ""
            except (IndexError, ValueError):
                raise NNTPDataError(f"Invalid {verb} response")
            return articleno, value

        return self._command_reply(code, message, parse, yz=verb == "XZHDR")

    def hdr(
        self,
        header: str,
        msgid_range: str | Range | None = None,
    ) -> Iterator[tuple[int, str]]:
        """HDR command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Provides access to specific fields from an article specified by
        message-id, or from a specified article or range of articles in the
        currently selected newsgroup.

        See <https://tools.ietf.org/html/rfc3977#section-8.5>

        Args:
            header: The header field to retrieve.
            msgid_range: A message-id as a string, or an article number as an
                integer, or a tuple of specifying a range of article numbers in
                the form (first, [last]) - if last is omitted then all articles
                after first are included. A msgid_range of None (the default)
                uses the current article.

        Yields:
            A 2-tuple giving the article number and value for the provided
            header field for each article in the given range.

        Raises:
            NNTPDataError: If the response from the server is malformed.
            NNTPReplyError: If no such article exists.
        """
        return self._hdr(header, msgid_range)

    def xhdr(
        self,
        header: str,
        msgid_range: str | Range | None = None,
    ) -> Iterator[tuple[int, str]]:
        """Generator for the XHDR command.

        Sends immediately; the returned iterator has the ownership rules of hdr().

        See hdr(). Values exclude their wire CRLF terminators. For a message-id
        request, an echoed matching identifier is returned as article number 0,
        like HDR. Numeric article selectors retain their server article numbers.
        """
        return self._hdr(header, msgid_range, verb="XHDR")

    def xzhdr(
        self,
        header: str,
        msgid_range: str | Range | None = None,
    ) -> Iterator[tuple[int, str]]:
        """Generator for the XZHDR command.

        Sends immediately; the returned iterator has the ownership rules of hdr().

        The compressed version of XHDR. See xhdr().

        A matching echoed message-id is returned as article number 0; values
        exclude their wire CRLF terminators, as in hdr() and xhdr().
        """
        return self._hdr(header, msgid_range, verb="XZHDR")

    @cached_property
    def overview_fmt(self) -> tuple[str, ...]:
        try:
            layout = tuple(self.list_overview_fmt())
            self._overview_full_fields = frozenset(
                name.casefold() for name, full in layout if full
            )
            return tuple(name for name, _full in layout)
        except NNTPError:
            self._overview_full_fields = frozenset()
            return (
                "Subject",
                "From",
                "Date",
                "Message-ID",
                "References",
                "Bytes",
                "Lines",
            )

    def _xover(
        self,
        range: str | Range | None = None,
        verb: str = "XOVER",
    ) -> Iterator[tuple[int, HeaderDict]]:
        # get overview fmt before entering generator
        fmt = self.overview_fmt
        full_fields: frozenset[str] = getattr(
            self, "_overview_full_fields", frozenset()
        )

        args = None
        if range is not None:
            args = utils.unparse_msgid_range(range)

        code, message = self.command(verb, args)
        if code != 224:
            raise self._unexpected(code, message)

        def parse(line: str) -> tuple[int, HeaderDict]:
            parts = line.rstrip("\r\n").split("\t")
            try:
                articleno = int(parts[0])
                fields = []
                for name, value in zip(fmt, parts[1:], strict=False):
                    if name.casefold() in full_fields and value:
                        label, colon, content = value.partition(":")
                        if colon and label.casefold() == name.casefold():
                            value = content.lstrip(" \t")
                    fields.append((name, value))
                overview = HeaderDict(fields)
            except (IndexError, ValueError):
                raise NNTPDataError(f"Invalid {verb} response")
            return articleno, overview

        return self._command_reply(code, message, parse, yz=verb == "XZVER")

    def over(
        self, msgid_range: str | Range | None = None
    ) -> Iterator[tuple[int, HeaderDict]]:
        """OVER command: yield article numbers and overview fields.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Accept a Message-ID, article number, range tuple or None for the
        current article. Results use the same overview parsing as xover(),
        including full-field normalization. Message-ID lookup is optional
        on servers; unsupported lookup raises NNTPPermanentError (503).

        See <https://www.rfc-editor.org/rfc/rfc3977#section-8.3>.
        """
        return self._xover(msgid_range, verb="OVER")

    def xover(
        self,
        range: Range | None = None,
    ) -> Iterator[tuple[int, HeaderDict]]:
        """XOVER command.

        Sends immediately; the returned iterator has the ownership rules of over().

        The XOVER command returns information from the overview database for
        the article(s) specified.

        <http://tools.ietf.org/html/rfc2980#section-2.8>

        Args:
            range: An article number as an integer, or a tuple of specifying a
                range of article numbers in the form (first, [last]). If last
                is omitted then all articles after first are included. A range
                of None (the default) uses the current article.

        Yields:
            A 2-tuple of the article number and a dictionary of the fields as
            given by the overview database for each available article in the
            specified range. The names of the fields that are returned are
            determined using the LIST OVERVIEW.FMT command if the server
            supports it, otherwise a fallback set of 'required' headers is
            used.

        Raises:
            NNTPReplyError: If no such article exists or the currently selected
                newsgroup is invalid.
        """
        return self._xover(range)

    def xzver(
        self,
        range: Range | None = None,
    ) -> Iterator[tuple[int, HeaderDict]]:
        """XZVER command.

        Sends immediately; the returned iterator has the ownership rules of over().

        The compressed version of XHDR. See xover().
        """
        return self._xover(range, verb="XZVER")

    def xpat(
        self,
        header: str,
        msgid_range: str | Range,
        *pattern: str,
    ) -> Iterator[str]:
        """XPAT command.

        Sends immediately. Consume, close or drop the returned iterator before
        another command; retaining it unread raises NNTPSyncError on that command.

        Used to retrieve specific headers from specific articles, based on
        pattern matching on the contents of the header.

        See <https://tools.ietf.org/html/rfc2980#section-2.9>

        Args:
            header: The header field to match against.
            msgid_range: An article number as an integer, or a tuple of
                specifying a range of article numbers in the form (first,
                [last]). If last is omitted then all articles after first are
                included.

        Yields:
            Not sure of the format but the value of the header will be part of
            it.

        Raises:
            NNTPReplyError: If no such article exists.
        """
        args = " ".join([header, utils.unparse_msgid_range(msgid_range), *pattern])

        code, message = self.command("XPAT", args)
        if code != 221:
            raise self._unexpected(code, message)

        return self._command_reply(code, message, str.strip)

    def xfeature_compress_gzip(self, terminator: bool = False) -> bool:
        """XFEATURE COMPRESS GZIP command."""
        args = "TERMINATOR" if terminator else None

        code, message = self.command("XFEATURE COMPRESS GZIP", args)
        if code != 290:
            raise self._unexpected(code, message)

        return True

    def _post_body(self, body: str | bytes | Iterable[bytes]) -> Iterator[bytes]:
        """Yield validated, CRLF-normalized and dot-stuffed body lines."""
        if isinstance(body, str):
            body = body.encode(self.encoding, self.errors)
        if isinstance(body, bytes):
            body = io.BytesIO(body)
        for chunk in body:
            # Iterable items are lines, but may themselves contain LF breaks.
            # An explicit empty item is a blank line, as in the original API.
            lines: Iterable[bytes] = io.BytesIO(chunk) if chunk else (b"",)
            for line in lines:
                if line.endswith(b"\r\n"):
                    line = line[:-2]
                elif line.endswith(b"\n"):
                    line = line[:-1]
                if b"\0" in line or b"\r" in line:
                    raise NNTPDataError("Illegal characters found")
                if line.startswith(b"."):
                    line = b"." + line
                yield line + b"\r\n"

    def _transfer_article(
        self,
        verb: str,
        args: str | None,
        headers: Mapping[str, str] | None,
        body: str | bytes | Iterable[bytes],
        *,
        ready: int,
        accepted: int,
    ) -> str:
        """Preflight an entire article, transfer it, and return the final text."""
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b") as article:
            article.write(utils.unparse_headers(headers or {}).encode(self.encoding))
            for line in self._post_body(body):
                article.write(line)
            article.write(b".\r\n")
            article.seek(0)

            try:
                code, message = self.command(verb, args)
                if code != ready:
                    raise self._unexpected(code, message)
                while chunk := article.read(65536):
                    self.socket.sendall(chunk)
                code, message = self.status()
            except TimeoutError as exc:
                # The server may hold a partial article or a delayed status;
                # neither state permits safely sending another command.
                with contextlib.suppress(OSError):
                    self.close()
                if isinstance(exc, NNTPTimeoutError):
                    raise
                raise NNTPTimeoutError(f"{verb} article transfer timed out") from exc

        if code != accepted:
            raise self._unexpected(code, message)
        return message

    def ihave(
        self,
        message_id: str,
        headers: Mapping[str, str] | None = None,
        body: str | bytes | Iterable[bytes] = b"",
    ) -> bool:
        """Offer an already-posted article for transfer using IHAVE.

        The complete article is prepared before IHAVE is sent, with the same
        header validation, CRLF normalization, dot-stuffing and spooled-file
        limit as post(). Only a 335 response permits transmission; a final
        235 returns True. Responses 435 (not wanted), 436 (retry later) and
        437 (rejected) raise NNTPTemporaryError under the existing 4xx
        exception hierarchy; inspect the code to decide whether to retry.

        Use a server permitting article transfers, usually with reader=False.
        Supply an already complete article's headers, including Message-ID;
        this method does not generate or rewrite them. The offered ID need
        not match a supplied Message-ID header, though matching is recommended.

        Raises:
            ValueError: If the offered Message-ID is not bracketed printable
                ASCII of at most 250 characters, or a header contains CR/LF.
            NNTPDataError: If the body contains NUL or bare CR.
            NNTPTimeoutError: If transfer or status reading times out. The
                connection is closed; no transfer is retried automatically.

        See <https://www.rfc-editor.org/rfc/rfc3977#section-6.3.2>.
        """
        if (
            len(message_id) > 250
            or re.fullmatch(r"<[\x21-\x3b\x3d\x3f-\x7e]+>", message_id) is None
        ):
            raise ValueError("Invalid IHAVE Message-ID")
        self._transfer_article(
            "IHAVE", message_id, headers, body, ready=335, accepted=235
        )
        return True

    def post(
        self,
        headers: Mapping[str, str] | None = None,
        body: str | bytes | Iterable[bytes] = b"",
    ) -> str | bool:
        """POST command.

        Args:
            headers: A dictionary of headers.
            body: A string, bytes or binary file-like object containing the post
                content.

        Raises:
            NNTPDataError: If binary characters are detected in the message
                body.
            ValueError: If a header name or value contains CR or LF.
            NNTPTimeoutError: If transfer or status reading times out. The
                connection is closed; the server may already have accepted
                the article, so no automatic retry is attempted.

        Returns:
            A value that evaluates to true if posting the message succeeded.
            (See note for further details)

        Note:
            '\\n' line terminators are converted to '\\r\\n'

        Note:
            Though not part of any specification it is common for usenet
            servers to return the message-id for a successfully posted message.
            If a message-id is identified in the response from the server then
            that message-id will be returned by the function, otherwise True
            will be returned.

        Note:
            The entire article is prepared before POST is sent, using a
            temporary file for articles larger than 1 MiB. Illegal characters
            (bare carriage returns '\\r' and null characters '\\0') raise
            NNTPDataError without posting a truncated article. Iterable body
            items are treated as lines and consumed before contacting the server.
        """
        message = self._transfer_article(
            "POST", None, headers, body, ready=340, accepted=240
        )
        # return message-id possible
        message_id = re.search(r"<[^<>\s]+>", message)
        if message_id is not None:
            return message_id.group()

        return True
