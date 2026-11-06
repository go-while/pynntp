"""Offline tests for the integration-test helpers in tests/integration/portable.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration import portable
from tests.scripted import ReadArticle, ScriptedServer

if TYPE_CHECKING:
    from collections.abc import Callable

NEW = "<new@example.test>"
HEADERS = {"Newsgroups": "local.test", "Message-ID": NEW, "Subject": "s", "From": "f"}


def lagging_group(polls_before_listed: int) -> dict[str, object]:
    """A script where STAT finds NEW at once but GROUP/XHDR list it only later."""
    calls = {"group": 0}

    def group(_line: str) -> bytes:
        calls["group"] += 1
        last = 2 if calls["group"] > polls_before_listed else 1
        return f"211 {last} 1 {last} local.test\r\n".encode()

    def xhdr(line: str) -> bytes:
        lines = ["1 <old@example.test>"]
        if line.endswith("-2"):
            lines.append(f"2 {NEW}")
        return ("221 Message-ID\r\n" + "\r\n".join(lines) + "\r\n.\r\n").encode()

    return {
        "POST": ReadArticle(b"340 send\r\n", b"240 article received\r\n"),
        "STAT": f"223 0 {NEW}\r\n".encode(),
        "GROUP": group,
        "XHDR": xhdr,
    }


def test_post_and_wait_waits_for_the_group(
    scripted_server: Callable[..., ScriptedServer],
) -> None:
    server = scripted_server(lagging_group(polls_before_listed=2))
    client = server.client()
    assert portable.post_and_wait(client, HEADERS, b"body\n") == NEW
    assert [line.split()[0] for line in server.received].count("GROUP") == 3
    assert server.received[-1] == "XHDR Message-ID 1-2"


def test_wait_for_article_times_out_when_never_listed(
    scripted_server: Callable[..., ScriptedServer],
) -> None:
    server = scripted_server(lagging_group(polls_before_listed=10**6))
    client = server.client()
    with pytest.raises(AssertionError, match=r"not in local\.test"):
        portable.wait_for_article(client, NEW, "local.test", timeout=0.5)


def test_wait_for_article_retries_430(
    scripted_server: Callable[..., ScriptedServer],
) -> None:
    replies = iter([b"430 no such article\r\n", f"223 0 {NEW}\r\n".encode()])
    server = scripted_server({"STAT": lambda _line: next(replies)})
    portable.wait_for_article(server.client(), NEW, timeout=5)
    assert server.received.count(f"STAT {NEW}") == 2


def test_check_posted_accepts_true_or_the_id() -> None:
    portable.check_posted(NEW, NEW)
    portable.check_posted(True, NEW)
    with pytest.raises(AssertionError):
        portable.check_posted("<other@example.test>", NEW)
