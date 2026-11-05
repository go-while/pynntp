from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tests.scripted import ScriptedServer

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.fixture
def scripted_server() -> Iterator[Callable[..., ScriptedServer]]:
    """Start scripted NNTP servers; all of them are stopped after the test.

    Usage: ``server = scripted_server({"DATE": b"111 20260101000000\\r\\n"})``,
    then ``client = server.client()``. Arguments are those of ScriptedServer.
    """
    servers: list[ScriptedServer] = []

    def start(*args: Any, **kwargs: Any) -> ScriptedServer:  # noqa: ANN401 (passed on)
        server = ScriptedServer(*args, **kwargs)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.stop()
