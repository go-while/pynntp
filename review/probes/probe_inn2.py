import sys, uuid
sys.path.insert(0, sys.argv[1])
import nntp

def run(name, fn):
    print(f"== {name}")
    c = nntp.NNTPClient("localhost")
    try:
        r = fn(c)
        print("   ->", repr(r)[:500])
    except Exception as e:
        print("   !!", type(e).__name__, e)
    try:
        print("   after: DATE ->", c.date())
    except Exception as e:
        print("   after: DATE !!", type(e).__name__, e)
    try: c.close()
    except Exception: pass

def rng(c):
    t, f, l, g = c.group("local.test"); return f, l
run("xhdr Subject", lambda c: list(c.xhdr("Subject", rng(c))))
run("xhdr Subject by msgid", lambda c: list(c.xhdr("Message-ID", rng(c)))[:1] and list(c.xhdr("Subject", list(c.xhdr("Message-ID", rng(c)))[0][1])))
run("xover", lambda c: list(c.xover(rng(c)))[-1])
run("over-fields Xref (full) value", lambda c: dict(list(c.xover(rng(c)))[-1][1]))
run("list_overview_fmt", lambda c: list(c.list_overview_fmt()))
run("list_headers", lambda c: list(c.list_headers()))
run("list_headers RANGE", lambda c: list(c.list_headers("RANGE")))
run("list_active_times", lambda c: list(c.list_active_times())[:3])
run("list_extensions", lambda c: list(c.list_extensions()))
run("capabilities", lambda c: list(c.capabilities()))
run("xpat", lambda c: list(c.xpat("Subject", rng(c), "*dot*")))
def abandon(c):
    for _ in c.list_active():
        break
    return c.group("local.test")
run("break out of list_active, then GROUP", abandon)
def nextcap(c):
    return next(c.capabilities())
run("next(capabilities())", nextcap)
def article_noblank(c):
    f, l = rng(c)
    return c.article(l)[0]
run("article(last)", article_noblank)
tag2 = uuid.uuid4().hex[:8]
def illegal(c):
    try:
        c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": f"illegal {tag2}"}, b"ok line\nbad\0line\nmore\n")
    except Exception as e:
        print("   post raised", type(e).__name__, e)
    return [(n, s) for n, s in c.xhdr("Subject", (rng(c)[0],)) if tag2 in s], c.body(rng(c)[1])
run("post illegal NUL then look", illegal)
tag3 = uuid.uuid4().hex[:8]
def inj(c):
    r = c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": f"inj {tag3}\r\nX-Injected: yes"}, "b\n")
    l = rng(c)[1]
    return r, c.head(l).get("X-Injected")
run("post header with CRLF in value", inj)
def post_ret(c):
    return c.post({"From": "t <t@example.invalid>", "Newsgroups": "local.test", "Subject": "ret"}, "x\n")
run("post return value", post_ret)
def dq(c):
    c.quit(); c.quit()
run("double quit", dq)
def stat_unknown(c):
    return c.command("STAT")
run("command STAT (no article selected)", stat_unknown)
def body_bad_msgid(c):
    return c.body("<nonexistent@x>")
run("body nonexistent", body_bad_msgid)
def ctx():
    with nntp.NNTPClient("localhost") as c:
        c.quit()
try:
    ctx(); print("ctx quit ok")
except Exception as e:
    print("ctx quit !!", type(e).__name__, e)
def ctx2():
    with nntp.NNTPClient("localhost") as c:
        raise KeyError("user error")
try:
    ctx2()
except Exception as e:
    print("ctx user error propagates as", type(e).__name__, e)
