"""A scripted NNTP server for offline tests.

The server listens on 127.0.0.1 on a free port, sends a greeting and answers
each command line the client sends from a script. It records what it receives,
so a test can check both sides of the conversation without a real server.

Script values (the reply to one command line):

- ``bytes``: sent as is, so a test controls the exact framing.
- a sequence of ``bytes`` and ``float``: the bytes are sent one after the
  other, a float pauses that many seconds. Use it to split a reply over
  several reads.
- ``ReadArticle``: for POST and IHAVE; sends ``first``, reads the article up to
  the terminating ``.`` line, stores it in ``articles``, then sends ``then``.
- ``CLOSE``: closes the connection without a reply.
- a callable taking the command line and returning one of the above.

A command line is looked up whole first (``"GROUP local.test"``), then by its
upper-cased first word (``"GROUP"``). Unknown commands get ``default``.
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO, Callable, Union

import nntp

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass(frozen=True)
class ReadArticle:
    """Read an article after sending ``first``, then send ``then``."""

    first: bytes
    then: bytes


class _Close:
    """Marker: close the connection instead of replying."""


CLOSE = _Close()

Step = Union[bytes, float]
Reply = Union[bytes, "Sequence[Step]", ReadArticle, _Close, Callable[[str], "Reply"]]

DEFAULT_SCRIPT: dict[str, Reply] = {
    "MODE READER": b"200 reader ready\r\n",
    "QUIT": b"205 bye\r\n",
}


class ScriptedServer:
    """Scripted NNTP server; see the module docstring."""

    def __init__(
        self,
        script: Mapping[str, Reply] | None = None,
        *,
        greeting: bytes = b"200 scripted server ready\r\n",
        default: Reply = b"500 unknown command\r\n",
    ) -> None:
        self.script: dict[str, Reply] = {**DEFAULT_SCRIPT, **(script or {})}
        self.greeting = greeting
        self.default = default
        # every command line received, without CRLF, over all connections
        self.received: list[str] = []
        # articles received by ReadArticle replies, as raw lines with CRLF
        self.articles: list[list[bytes]] = []
        self.connections = 0
        self._lock = threading.Lock()
        self._conns: list[socket.socket] = []
        self._clients: list[nntp.NNTPClient] = []
        self._threads: list[threading.Thread] = []
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.port: int = self._listener.getsockname()[1]
        self._accept_thread = threading.Thread(target=self._accept, daemon=True)
        self._accept_thread.start()

    def client(self, **kwargs: object) -> nntp.NNTPClient:
        """Connect an ``NNTPClient`` to this server; ``stop()`` closes it."""
        client = nntp.NNTPClient("127.0.0.1", self.port, **kwargs)  # type: ignore[arg-type]
        self._clients.append(client)
        return client

    def stop(self) -> None:
        """Close clients, listener and connections; wait for the threads."""
        for client in self._clients:
            client.socket.close()
        # shutdown() wakes the thread blocked in accept(); close() alone doesn't
        with contextlib.suppress(OSError):
            self._listener.shutdown(socket.SHUT_RDWR)
        self._listener.close()
        with self._lock:
            conns = list(self._conns)
        for conn in conns:
            with contextlib.suppress(OSError):
                conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        self._accept_thread.join(timeout=5)
        for thread in self._threads:
            thread.join(timeout=5)

    def _accept(self) -> None:
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            with self._lock:
                self.connections += 1
                self._conns.append(conn)
            thread = threading.Thread(target=self._serve, args=(conn,), daemon=True)
            self._threads.append(thread)
            thread.start()

    def _lookup(self, line: str) -> Reply:
        if line in self.script:
            return self.script[line]
        verb = line.split(" ", 1)[0].upper()
        return self.script.get(verb, self.default)

    def _serve(self, conn: socket.socket) -> None:
        reader = conn.makefile("rb")
        try:
            conn.sendall(self.greeting)
            while True:
                raw = reader.readline()
                if not raw:
                    return
                line = raw.rstrip(b"\r\n").decode("utf-8", "surrogateescape")
                with self._lock:
                    self.received.append(line)
                if not self._reply(conn, reader, line, self._lookup(line)):
                    return
        except OSError:
            return
        finally:
            reader.close()
            conn.close()

    def _reply(
        self,
        conn: socket.socket,
        reader: BinaryIO,
        line: str,
        reply: Reply,
    ) -> bool:
        """Send one reply; return False if the connection is to be closed."""
        while callable(reply):
            reply = reply(line)
        if isinstance(reply, _Close):
            return False
        if isinstance(reply, ReadArticle):
            conn.sendall(reply.first)
            article: list[bytes] = []
            while True:
                data = reader.readline()
                if not data or data == b".\r\n":
                    break
                article.append(data)
            with self._lock:
                self.articles.append(article)
            conn.sendall(reply.then)
            return True
        if isinstance(reply, bytes):
            conn.sendall(reply)
            return True
        for step in reply:
            if isinstance(step, float):
                time.sleep(step)
            else:
                conn.sendall(step)
        return True
