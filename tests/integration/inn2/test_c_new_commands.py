"""STAT, LISTGROUP and OVER against INN."""

from uuid import uuid4

import nntp
from tests.integration.portable import post_and_wait, require


def test_stat_listgroup_and_over() -> None:
    require("OVER")
    require("POST")
    message_id = f"<pynntp-commands-{uuid4().hex}@example.test>"
    with nntp.NNTPClient("localhost") as client:
        post_and_wait(
            client,
            {
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": "local.test",
                "Message-ID": message_id,
                "Subject": "New commands regression",
            },
            b"New commands body\n",
        )
        assert client.stat(message_id) == (0, message_id)
        _total, _first, last, _group = client.group("local.test")
        assert client.stat(last) == (last, message_id)
        assert client.stat() == (last, message_id)
        assert list(client.listgroup("local.test", (last, last))) == [last]
        numbers = list(client.listgroup())
        assert last in numbers
        assert numbers == sorted(set(numbers))
        entries = list(client.over(last))
        assert len(entries) == 1
        assert entries[0][0] == last
        assert entries[0][1]["Message-ID"] == message_id
        if "OVER MSGID" in set(client.capabilities()):
            by_id = list(client.over(message_id))
            assert len(by_id) == 1
            assert by_id[0][0] in (0, last)
            assert by_id[0][1]["Message-ID"] == message_id
        else:
            try:
                by_id = list(client.over(message_id))
            except nntp.NNTPPermanentError as error:
                if error.code != 503:  # Message-ID form is optional.
                    raise
            else:
                assert len(by_id) == 1
                assert by_id[0][0] in (0, last)
                assert by_id[0][1]["Message-ID"] == message_id
        assert client.date().tzinfo is not None
