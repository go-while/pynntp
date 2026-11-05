"""Probe pynntp behaviour against a live INN on localhost:119."""
import sys, traceback, uuid, socket
from datetime import datetime, timezone, timedelta
sys.path.insert(0, sys.argv[1])
import nntp
from nntp.nntp import NNTPSyncError

def run(name, fn):
    print(f"== {name}")
    try:
        r = fn()
        print("   ->", repr(r)[:400])
    except Exception as e:
        print("   !!", type(e).__name__, e)

def raw(cmds):
    s = socket.create_connection(("localhost", 119), timeout=5)
    f = s.makefile("rb")
    out = [f.readline()]
    for c in cmds:
        s.sendall(c.encode() + b"\r\n")
        out.append(f.readline())
    s.close()
    return out

c = nntp.NNTPClient("localhost")
print("raw LIST ACTIVE local.*:", list(c.list("ACTIVE", "local.*")))
run("list_active local.general (Newsgroup low/high)", lambda: list(c.list_active("local.general")))
run("list_active junk", lambda: list(c.list_active("junk")))
since = datetime(2000, 1, 1, tzinfo=timezone.utc)
run("newgroups(2000)", lambda: list(c.newgroups(since)))
run("newnews(*, 2000)", lambda: list(c.newnews("*", since))[:3])
print("raw NEWGROUPS UTC vs GMT:", raw(["NEWGROUPS 20000101 000000 UTC", "NEWGROUPS 20000101 000000 GMT", "QUIT"]))

# dot-stuffing round trip
tag = uuid.uuid4().hex[:8]
body = f"first line {tag}\n.leading dot line\n..two dots\n.\nlast\n"
run("post dot-body", lambda: c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": f"dot {tag}"}, body))
total, first, last, g = c.group("local.test")
run("body(last) dot-unstuff", lambda: c.body(last))
print("   expected:", body.replace("\n", "\r\n").encode())
run("head(last)", lambda: dict(c.head(last)))
# HDR (RFC 3977 225) vs XHDR (221)
run("hdr Subject", lambda: list(c.hdr("Subject", (first, last)))[:2])
run("xhdr Subject", lambda: list(c.xhdr("Subject", (first, last)))[:2])
run("xover", lambda: list(c.xover((last, last))))
run("list_overview_fmt", lambda: list(c.list_overview_fmt()))
run("list_headers", lambda: list(c.list_headers()))
run("list_active_times", lambda: list(c.list_active_times())[:2])
run("list_extensions", lambda: list(c.list_extensions()))
run("capabilities", lambda: list(c.capabilities()))
run("date", lambda: c.date())
run("xpat", lambda: list(c.xpat("Subject", (first, last), f"*{tag}*")))
# generator abandonment
def abandon():
    for _ in c.list_active():
        break
    return c.group("local.test")
run("break out of list_active, then GROUP", abandon)
c2 = nntp.NNTPClient("localhost")
def nextcap():
    v = next(c2.capabilities())
    return v, c2.date()
run("next(capabilities()) then date()", nextcap)
# lazy generator: no command sent until iteration
c3 = nntp.NNTPClient("localhost")
def lazy():
    g = c3.list_newsgroups("nonexistent.*")
    g2 = c3.list_active("local.*")
    return list(g2), list(g)
run("two generators created then consumed in reverse order", lazy)
# post with illegal char: does it post truncated?
tag2 = uuid.uuid4().hex[:8]
run("post illegal NUL", lambda: c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": f"illegal {tag2}"}, b"ok line\nbad\0line\nmore\n"))
run("was truncated article posted?", lambda: list(c.xpat("Subject", (first,), f"*{tag2}*")))
# header injection
tag3 = uuid.uuid4().hex[:8]
run("post header with CRLF in value", lambda: c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": f"inj {tag3}\r\nX-Injected: yes"}, "b\n"))
run("injected header present?", lambda: [dict(c.head(n)).get("X-Injected") for n, s in c.xhdr("Subject", (first,)) if tag3 in s])
run("quit", c.quit)
run("quit again (double quit)", c.quit)
run("close after quit", c.close)
