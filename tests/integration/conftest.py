"""Skip the integration tests when no NNTP server is listening.

They run against an INN on localhost (see inn2/setup.sh). Without one, a
plain ``pytest`` (for example from the sdist) skips them instead of failing.
Set ``PYNNTP_INTEGRATION=1`` to require the server: then they run and fail
if it is missing, so CI can't pass by skipping them.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

HOST = "localhost"
PORT = 119


def _server_listening() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=1):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(
    config: pytest.Config,  # noqa: ARG001
    items: Sequence[pytest.Item],
) -> None:
    if os.environ.get("PYNNTP_INTEGRATION") == "1" or _server_listening():
        return
    reason = f"no NNTP server on {HOST}:{PORT}; PYNNTP_INTEGRATION=1 requires it"
    skip = pytest.mark.skip(reason=reason)
    here = Path(__file__).parent
    for item in items:
        if here in item.path.parents:
            item.add_marker(skip)
