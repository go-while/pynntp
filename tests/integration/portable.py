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


def connect() -> nntp.NNTPClient:
    """Connect to the server under test (offline tests replace this)."""
    return nntp.NNTPClient("localhost")


@functools.cache
def capabilities() -> frozenset[str]:
    """Return what the server on localhost lists in CAPABILITIES, upper-cased.

    Each line is included whole and as its first word, so both "COMPRESS" and
    "COMPRESS DEFLATE" match. A server without CAPABILITIES gives an empty set.
    """
    with connect() as client:
        try:
            lines = [line.upper() for line in client.capabilities()]
        except nntp.NNTPPermanentError as exc:
            # 500/501: no CAPABILITIES at all. Other errors (480, 400, 503)
            # are failures, not a missing feature.
            if exc.code not in (500, 501):
                raise
            return frozenset()
    found = set(lines)
    found.update(line.split()[0] for line in lines if line.split())
    return frozenset(found)


def require(capability: str) -> None:
    """Skip the test unless the server advertises the capability."""
    if capability.upper() not in capabilities():
        pytest.skip(f"the server does not advertise {capability}")


def require_inn() -> None:
    """Skip the test unless the server is INN (IMPLEMENTATION INN ...).

    For tests of INN's own setup rather than of NNTP, such as the junk group
    and the default newsgroups that inn2/setup.sh leaves in place.
    """
    if not any(line.startswith("IMPLEMENTATION INN") for line in capabilities()):
        pytest.skip("tests INN's own setup")


def check_posted(result: str | bool, message_id: str) -> None:
    """Assert that post() or ihave() succeeded for message_id.

    POST returns the Message-ID when the server puts it in the 240 reply, and
    True when it does not (NewsCache, for example).
    """
    assert result in (message_id, True)


def wait_for_article(
    client: nntp.NNTPClient,
    message_id: str,
    group: str | None = None,
    timeout: float = POST_WAIT,
) -> None:
    """Wait until message_id is readable, and listed in group if given.

    Some servers (Diablo) make a posted article readable through their feed,
    a moment after the 240 reply, and STAT by Message-ID can succeed before
    GROUP and the overview show it. With group, this also waits until XHDR
    Message-ID over the group's last RECENT articles lists message_id; that
    is selected afterwards. Raises the last error, or AssertionError, after
    timeout.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            client.stat(message_id)
            if group is None or _in_group(client, message_id, group):
                return
            error: Exception = AssertionError(f"{message_id} not in {group}")
        except nntp.NNTPTemporaryError as exc:
            error = exc
        if time.monotonic() >= deadline:
            raise error
        time.sleep(0.2)


RECENT = 100


def _in_group(client: nntp.NNTPClient, message_id: str, group: str) -> bool:
    """Tell whether XHDR over the last RECENT articles of group lists message_id."""
    _total, first, last, _name = client.group(group)
    if last < first:
        return False
    found = client.xhdr("Message-ID", f"{max(first, last - RECENT + 1)}-{last}")
    return message_id in {value.strip() for _number, value in found}


def post_and_wait(
    client: nntp.NNTPClient,
    headers: Mapping[str, str],
    body: str | bytes | Iterable[bytes] = b"",
) -> str:
    """Post an article that has a Message-ID header and wait until it is readable.

    Also waits until it is listed in the first group of its Newsgroups header,
    which is then selected.

    Returns:
        The Message-ID from the headers.
    """
    message_id = headers["Message-ID"]
    check_posted(client.post(headers, body), message_id)
    group = headers.get("Newsgroups", "").split(",")[0].strip() or None
    wait_for_article(client, message_id, group)
    return message_id
