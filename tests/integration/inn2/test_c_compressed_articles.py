"""POST/IHAVE article writes through RFC 8054 compression on disposable INN."""

import re
from datetime import datetime, timezone
from email.utils import format_datetime
from uuid import uuid4

import pytest

import nntp
from tests.integration.portable import (
    check_posted,
    post_and_wait,
    require,
    wait_for_article,
)


def _inn_version(capabilities: list[str]) -> tuple[int, ...]:
    """INN's version from CAPABILITIES, or (99,) for other servers."""
    for line in capabilities:
        match = re.match(r"IMPLEMENTATION INN (\d+)\.(\d+)\.(\d+)", line)
        if match:
            return tuple(int(part) for part in match.groups())
    return (99,)


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_compressed_article_round_trip(verb: str) -> None:
    require("COMPRESS")
    require(verb)
    with nntp.NNTPClient("localhost", reader=False) as client:
        if _inn_version(list(client.capabilities())) < (2, 7, 2):
            pytest.skip("nnrpd before INN 2.7.2 hangs on compressed uploads")
        client.compress()
        for _ in range(2):
            message_id = f"<pynntp-compressed-{uuid4().hex}@example.test>"
            headers = {
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": "local.test",
                "Date": format_datetime(datetime.now(timezone.utc)),
                "Message-ID": message_id,
                "Subject": "Compressed article regression",
            }
            # Cross transport chunks, with line lengths acceptable to INN.
            lines = [b".first", b".", *[b"x" * 200] * 400, b"last"]
            if verb == "POST":
                post_and_wait(client, headers, iter(lines))
            else:
                check_posted(client.ihave(message_id, headers, iter(lines)), message_id)
                wait_for_article(client, message_id, group="local.test")
            assert client.stat(message_id) == (0, message_id)
            assert (
                client.body(message_id, decode=False) == b"\r\n".join(lines) + b"\r\n"
            )
            assert client.head(message_id)["Subject"] == "Compressed article regression"
            assert client.date().tzinfo is not None
        assert client.compressed
