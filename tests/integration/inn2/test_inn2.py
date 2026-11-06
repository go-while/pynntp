import os
from unittest import mock
from uuid import uuid4

import pytest

import nntp
from nntp.types import SSLMode
from tests.integration.portable import check_posted, post_and_wait, require, require_inn

TEST_GROUPS = {"local.general", "local.test"}
INN_DEFAULT_GROUPS = TEST_GROUPS | {
    "control",
    "control.cancel",
    "control.checkgroups",
    "control.newgroup",
    "control.rmgroup",
    "junk",
}


def newsgroup_names(nntp_client: nntp.NNTPClient) -> set[str]:
    """Return active group names, independently of optional descriptions."""
    return {group.name for group in nntp_client.list_active()}


def test_inn_default_newsgroups() -> None:
    require_inn()
    with nntp.NNTPClient("localhost") as client:
        assert {name for name, _ in client.list_newsgroups()} == INN_DEFAULT_GROUPS


def test_nntp_client() -> None:
    nntp_client = nntp.NNTPClient("localhost")
    newsgroups = newsgroup_names(nntp_client)
    assert newsgroups >= TEST_GROUPS


def test_context_manager() -> None:
    """
    https://docs.python.org/3/reference/datamodel.html#context-managers
    """
    with nntp.NNTPClient("localhost") as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS


def test_context_manager_on_close() -> None:
    """
    nntp_client.close() should normally not be called within the context manager.
    """
    with nntp.NNTPClient("localhost") as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS
        nntp_client.close()


def test_context_manager_on_quit() -> None:
    """
    nntp_client.quit() should normally not be called within the context manager.
    """
    with nntp.NNTPClient("localhost") as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS
        nntp_client.quit()


def test_nntp_client_without_ssl() -> None:
    with nntp.NNTPClient("localhost", use_ssl=False) as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS


@mock.patch.dict(os.environ, {"PYNNTP_TLS_INSECURE": "1"})
def test_nntp_client_with_ssl() -> None:
    with nntp.NNTPClient("localhost", 563, use_ssl=True) as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS


@mock.patch.dict(os.environ, {"PYNNTP_TLS_INSECURE": "1"})
def test_nntp_client_with_ssl_starttls() -> None:
    require("STARTTLS")
    with nntp.NNTPClient(
        "localhost", use_ssl=True, ssl_mode=SSLMode.STARTTLS
    ) as nntp_client:
        newsgroups = newsgroup_names(nntp_client)
        assert newsgroups >= TEST_GROUPS


@pytest.mark.parametrize(
    "newsgroup",
    [
        "local.general",
        "local.test",
        pytest.param(
            "junk",
            marks=pytest.mark.xfail(raises=nntp.nntp.NNTPTemporaryError, strict=True),
        ),
    ],
)
def test_post(newsgroup: str) -> None:
    if newsgroup == "junk":
        require_inn()
    message_id = f"<pynntp-post-{uuid4().hex}@example.test>"
    headers = {
        "Subject": f"Test post to {newsgroup}",
        "From": "GitHub Actions <actions@github.com>",
        "Newsgroups": newsgroup,
        "Message-ID": message_id,
    }
    with nntp.NNTPClient("localhost") as nntp_client:
        check_posted(
            nntp_client.post(
                headers=headers, body=f"This is a test post to {newsgroup}"
            ),
            message_id,
        )


@pytest.mark.parametrize("newsgroup", ["local.general", "local.test", "junk"])
def test_list_active(newsgroup: str) -> None:
    if newsgroup == "junk":
        require_inn()
    with nntp.NNTPClient("localhost") as nntp_client:
        articles = list(nntp_client.list_active(newsgroup))
        assert len(articles) == 1
        name, low, high, status = articles[0]
        assert name == newsgroup
        assert low >= 0
        assert high >= 0
        assert low <= high + 1
        assert status == ("n" if newsgroup == "junk" else "y")
        if newsgroup != "junk":
            total, first, last, _group = nntp_client.group(newsgroup)
            assert high == last
            if total:
                assert low == first


@pytest.mark.parametrize(
    "newsgroup",
    [
        "local.general",
        "local.test",
        pytest.param(
            "junk",
            marks=pytest.mark.xfail(raises=nntp.nntp.NNTPTemporaryError, strict=True),
        ),
    ],
)
def test_article(newsgroup: str) -> None:
    if newsgroup == "junk":
        require_inn()
    message_id = f"<pynntp-article-{uuid4().hex}@example.test>"
    subject = f"Article regression {message_id}"
    body = f"This is a test article for {newsgroup}"
    with nntp.NNTPClient("localhost") as nntp_client:
        post_and_wait(
            nntp_client,
            {
                "Subject": subject,
                "From": "pynntp tests <test@example.test>",
                "Newsgroups": newsgroup,
                "Message-ID": message_id,
            },
            body,
        )
        total, first, last, group = nntp_client.group(newsgroup)
        assert total >= 1
        assert 0 < first <= last
        assert group == newsgroup
        _article_number, headers, received_body = nntp_client.article(message_id)
        assert headers["Message-ID"] == message_id
        assert headers["Newsgroups"] == newsgroup
        assert headers["Subject"] == subject
        assert received_body == f"{body}\r\n".encode()
