"""Run the integration tests only when asked to.

They post articles to an INN on localhost (see inn2/setup.sh), so they must
never run by accident against a real news server that happens to listen on
port 119. They are skipped unless ``PYNNTP_INTEGRATION=1`` is set; then they
run, and fail if the server is missing. CI and the test hosts set it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence


def pytest_collection_modifyitems(
    config: pytest.Config,  # noqa: ARG001
    items: Sequence[pytest.Item],
) -> None:
    if os.environ.get("PYNNTP_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(
        reason="integration tests post to the NNTP server on localhost:119; "
        "set PYNNTP_INTEGRATION=1 to run them"
    )
    here = Path(__file__).parent
    for item in items:
        if here in item.path.parents:
            item.add_marker(skip)
