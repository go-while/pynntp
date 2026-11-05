"""HDR's RFC 3977 success code against INN."""

from uuid import uuid4

import nntp


def test_hdr_message_id() -> None:
    message_id = f"<pynntp-hdr-{uuid4().hex}@example.test>"
    subject = f"HDR regression {message_id}"
    with nntp.NNTPClient("localhost") as client:
        client.post(
            {
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": "local.test",
                "Message-ID": message_id,
                "Subject": subject,
            },
            b"HDR test body\n",
        )
        values = list(client.hdr("Subject", message_id))
        assert [(number, value.rstrip("\r\n")) for number, value in values] == [
            (0, subject)
        ]
        assert client.date().tzinfo is not None
