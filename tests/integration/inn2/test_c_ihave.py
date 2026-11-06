"""IHAVE through the disposable INN's localhost reader permissions."""

from datetime import datetime, timezone
from email.utils import format_datetime
from uuid import uuid4

import nntp
from tests.integration.portable import check_posted, require, wait_for_article


def test_ihave_round_trip() -> None:
    require("IHAVE")
    message_id = f"<pynntp-ihave-{uuid4().hex}@example.test>"
    headers = {
        "From": "pynntp tests <test@example.test>",
        "Newsgroups": "local.test",
        "Date": format_datetime(datetime.now(timezone.utc)),
        "Message-ID": message_id,
        "Subject": "IHAVE regression",
    }
    with nntp.NNTPClient("localhost", reader=False) as client:
        check_posted(
            client.ihave(message_id, headers, b"first\n.dot\n.\nlast\n"), message_id
        )
        wait_for_article(client, message_id, group="local.test")
        assert client.stat(message_id) == (0, message_id)
        assert (
            client.body(message_id, decode=False) == b"first\r\n.dot\r\n.\r\nlast\r\n"
        )
        assert client.head(message_id)["Subject"] == "IHAVE regression"
        assert client.date().tzinfo is not None
