"""Eager command ownership with a real INN connection."""

from uuid import uuid4

import pytest

import nntp
from tests.integration.portable import post_and_wait, require


def test_unread_listgroup_and_over_ownership() -> None:
    require("OVER")
    require("POST")
    with nntp.NNTPClient("localhost") as client:
        post_and_wait(
            client,
            {
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": "local.test",
                "Subject": "Eager command regression",
                "Message-ID": f"<pynntp-eager-{uuid4().hex}@example.test>",
            },
            b"eager commands body\n",
        )
        reply = client.listgroup("local.test")
        with pytest.raises(nntp.nntp.NNTPSyncError):
            client.date()
        # This command has already selected the group and registered its reply.
        assert hasattr(reply, "close")
        reply.close()
        assert client.date().tzinfo is not None

        _total, first, last, _name = client.group("local.test")
        overview = client.over((first, last))
        with pytest.raises(nntp.nntp.NNTPSyncError):
            client.date()
        del overview  # Unstarted, dropped: the next command drains all rows.
        assert client.date().tzinfo is not None
