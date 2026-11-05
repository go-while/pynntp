[![Check](https://github.com/go-while/pynntp/actions/workflows/check.yml/badge.svg?branch=develop-01)](https://github.com/go-while/pynntp/actions/workflows/check.yml)

# pynntp

Python NNTP library.

This is a maintained fork of [greenbender/pynntp](https://github.com/greenbender/pynntp).

This package includes advanced NNTP features, including compressed headers.

The most important (useful) feature of this package over other nntp libraries is
the ability to use generators to produce data. This allows for streaming download
of large responses to say an XOVER command (which can produce gigabytes of data)
and allows you to process the data at the same time it is being received.
Meaning that memory use is minimal (even for the largest responses) and that
cycles aren't being wasted waiting on a blocking read (even in a single threaded
application).

Requires Python 3.10 or newer. The package has no dependencies and ships type
annotations (`py.typed`).

## Documentation

https://greenbender.github.io/pynntp/

At present the docs are generated from the docstrings. More explicit
documentation, including examples, is on the TODO list.

## Example

```python
import nntp

# implicit TLS on port 563; use SSLMode.STARTTLS on port 119 instead
with nntp.NNTPClient("news.example.com", 563, "user", "password", use_ssl=True) as client:
    print(client.date())  # datetime in UTC, e.g. 2026-11-05 21:58:07+00:00

    total, first, last, group = client.group("comp.lang.python")

    # replies are generators: lines are processed as they arrive
    if total:
        for number, overview in client.xover((max(first, last - 100), last)):
            print(number, overview["Subject"])

    message_id = client.post(
        {
            "From": "Me <me@example.com>",
            "Newsgroups": "misc.test",
            "Subject": "test",
        },
        "Hello\n",
    )
    print(message_id)  # the Message-ID the server reports, or True
```

One reply is read at a time. Leaving a `for` loop over a reply early is fine:
once nothing refers to the reply any more, the rest of it is read and dropped
before the next command. A reply you still hold in a variable counts as being
read, so the next command raises `NNTPSyncError` until you finish it, call its
`close()` or drop it:

```python
groups = client.list_active()
first_group = next(groups)
groups.close()  # or: del groups; or read it to the end
client.date()
```

Errors from the server raise subclasses of `nntp.NNTPError`.

## Supported Commands

NNTP commands that are currently supported include:

- CAPABILITIES
- MODE READER
- STARTTLS
- AUTHINFO USER/PASS (sent automatically when the server asks with 480)
- QUIT
- DATE
- HELP
- NEWGROUPS
- NEWNEWS
- LIST ACTIVE
- LIST ACTIVE.TIMES
- LIST HEADERS
- LIST NEWSGROUPS
- LIST OVERVIEW.FMT
- LIST EXTENSIONS
- GROUP
- NEXT
- LAST
- ARTICLE
- HEAD
- BODY (yEnc bodies are decoded and checked against their size and CRC)
- POST
- HDR
- XHDR
- XZHDR
- XOVER
- XZVER
- XPAT
- XFEATURE COMPRESS GZIP

## Development

```sh
pip install pytest mypy ruff
pytest                                  # offline tests; integration tests are skipped
ruff check nntp tests && ruff format --check nntp tests && mypy --strict nntp tests
```

The integration tests post articles to an INN server on localhost, so they run
only with `PYNNTP_INTEGRATION=1`, on a disposable machine:

```sh
sudo sh tests/integration/inn2/setup.sh   # Debian/Ubuntu: installs and configures inn2
PYNNTP_INTEGRATION=1 pytest
```

Each change adds a one-line changelog fragment in `changes/` (see
`changes/README.md`).
