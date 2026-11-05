"""XHDR's Message-ID form and values against INN."""

from uuid import uuid4

import nntp


def test_xhdr_by_message_id_and_number() -> None:
    message_id = f"<pynntp-xhdr-{uuid4().hex}@example.test>"
    subject = f"XHDR regression {message_id}"
    with nntp.NNTPClient("localhost") as client:
        assert (
            client.post(
                {
                    "From": "pynntp tests <test@example.test>",
                    "Newsgroups": "local.test",
                    "Message-ID": message_id,
                    "Subject": subject,
                },
                b"XHDR test body\n",
            )
            == message_id
        )
        assert list(client.xhdr("Subject", message_id)) == [(0, subject)]
        assert list(client.hdr("Subject", message_id)) == [(0, subject)]
        _total, _first, last, _group = client.group("local.test")
        assert list(client.xhdr("Subject", last)) == [(last, subject)]
        assert client.date().tzinfo is not None
