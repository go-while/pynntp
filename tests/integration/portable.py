"""Helpers that let the integration tests run against servers other than INN.

The tests were written against INN on localhost. Other servers (Diablo,
NewsCache) support fewer optional features, may omit the Message-ID from the
240 reply to POST, and may make a posted article readable only a moment later.
Tests use these helpers to skip what the server does not advertise and to
wait for their own articles.

Environment:
    PYNNTP_TLS_CAFILE: certificate of the server's TLS listener (default
        /etc/news/pynntp-cert.pem, which inn2/setup.sh creates).
    PYNNTP_POST_WAIT: seconds to wait for a posted article to become
        readable (default 10).
"""

from __future__ import annotations

import functools
import os
import time
from typing import TYPE_CHECKING

import pytest

import nntp

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

TLS_CAFILE = os.environ.get("PYNNTP_TLS_CAFILE", "/etc/news/pynntp-cert.pem")
POST_WAIT = float(os.environ.get("PYNNTP_POST_WAIT", "10"))


@functools.cache
def capabilities() -> frozenset[str]:
    """Return what the server on localhost lists in CAPABILITIES, upper-cased.

    Each line is included whole and as its first word, so both "COMPRESS" and
    "COMPRESS DEFLATE" match. A server without CAPABILITIES gives an empty set.
    """
    with nntp.NNTPClient("localhost") as client:
        try:
            lines = [line.upper() for line in client.capabilities()]
        except nntp.NNTPReplyError:
            return frozenset()
    found = set(lines)
    found.update(line.split()[0] for line in lines if line.split())
    return frozenset(found)


def require(capability: str) -> None:
    """Skip the test unless the server advertises the capability."""
    if capability.upper() not in capabilities():
        pytest.skip(f"the server does not advertise {capability}")


def check_posted(result: str | bool, message_id: str) -> None:
    """Assert that post() or ihave() succeeded for message_id.

    POST returns the Message-ID when the server puts it in the 240 reply, and
    True when it does not (NewsCache, for example).
    """
    assert result in (message_id, True)


def wait_for_article(
    client: nntp.NNTPClient, message_id: str, timeout: float = POST_WAIT
) -> None:
    """Wait until STAT finds message_id; raise the last error after timeout.

    Some servers (Diablo) make a posted article readable through their feed,
    a moment after the 240 reply.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            client.stat(message_id)
        except nntp.NNTPTemporaryError:  # noqa: PERF203 (polls a server)
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)
        else:
            return


def post_and_wait(
    client: nntp.NNTPClient,
    headers: Mapping[str, str],
    body: str | bytes | Iterable[bytes] = b"",
) -> str:
    """Post an article that has a Message-ID header and wait until it is readable.

    Returns:
        The Message-ID from the headers.
    """
    message_id = headers["Message-ID"]
    check_posted(client.post(headers, body), message_id)
    wait_for_article(client, message_id)
    return message_id
