"""POST/IHAVE article writes through RFC 8054 compression on disposable INN."""

from datetime import datetime, timezone
from email.utils import format_datetime
from uuid import uuid4

import pytest

import nntp


@pytest.mark.parametrize("verb", ["POST", "IHAVE"])
def test_compressed_article_round_trip(verb: str) -> None:
    with nntp.NNTPClient("localhost", reader=False) as client:
        capabilities = list(client.capabilities())
        if any(line.startswith("IMPLEMENTATION INN 2.6.") for line in capabilities):
            pytest.skip("nnrpd 2.6 stalls on compressed article input")
        # B9 adds public compress(); C13 exercises the already-agreed I6
        # boundary directly without requiring the session-feature branch.
        assert client.command("COMPRESS DEFLATE")[0] == 206
        client._start_compression()  # noqa: SLF001
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
            args = (message_id,) if verb == "IHAVE" else ()
            result = getattr(client, verb.lower())(
                *args, headers=headers, body=iter(lines)
            )
            assert result is True or result == message_id
            assert client.stat(message_id) == (0, message_id)
            assert (
                client.body(message_id, decode=False) == b"\r\n".join(lines) + b"\r\n"
            )
            assert client.head(message_id)["Subject"] == "Compressed article regression"
            assert client.date().tzinfo is not None
        assert client.compressed
