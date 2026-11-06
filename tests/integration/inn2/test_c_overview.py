"""Overview :full fields against INN."""

from uuid import uuid4

import nntp
from tests.integration.portable import post_and_wait, require


def test_overview_xref_has_no_field_prefix() -> None:
    require("OVER")
    require("POST")
    message_id = f"<pynntp-overview-{uuid4().hex}@example.test>"
    with nntp.NNTPClient("localhost") as client:
        post_and_wait(
            client,
            {
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": "local.test",
                "Message-ID": message_id,
                "Subject": "Overview regression",
            },
            b"Overview test body\n",
        )
        _total, _first, last, _group = client.group("local.test")
        entries = list(client.xover(last))
        assert len(entries) == 1
        number, fields = entries[0]
        assert number == last
        assert fields["Message-ID"] == message_id
        assert not fields["Xref"].casefold().startswith("xref:")
        assert f"local.test:{last}" in fields["Xref"]
