"""NEWGROUPS and NEWNEWS timestamp syntax against INN."""

from datetime import timedelta

import nntp
from tests.integration.portable import require


def test_newgroups_future() -> None:
    with nntp.NNTPClient("localhost") as client:
        future = client.date() + timedelta(days=1)
        assert list(client.newgroups(future)) == []


def test_newnews_future() -> None:
    require("NEWNEWS")
    with nntp.NNTPClient("localhost") as client:
        future = client.date() + timedelta(days=1)
        assert list(client.newnews("local.*", future)) == []
