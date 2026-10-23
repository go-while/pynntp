import sys, os, ssl
sys.path.insert(0, sys.argv[1])
import nntp
from nntp.types import SSLMode
c = nntp.NNTPClient("localhost")
t, f, l, g = c.group("local.test")
mid = c.head(l)["Message-ID"]
print("msgid", mid)
try:
    print("xhdr by msgid:", list(c.xhdr("Subject", mid)))
except Exception as e:
    print("xhdr by msgid !!", type(e).__name__, e)
c.close()
c = nntp.NNTPClient("localhost")
c.socket.sendall(b"POST\r\n"); print(c.status())
c.socket.sendall(b"From: a <a@b.invalid>\r\nNewsgroups: local.test\r\nSubject: raw\r\n\r\nx\r\n.\r\n"); print("raw POST reply:", c.status())
c.close()
# with-block + break
try:
    with nntp.NNTPClient("localhost") as c:
        for grp in c.list_active():
            break
    print("with+break ok")
except Exception as e:
    print("with+break !!", type(e).__name__, e, "| context:", repr(e.__context__))
try:
    with nntp.NNTPClient("localhost") as c:
        for grp in c.list_active():
            raise KeyError("user error")
except Exception as e:
    print("with+user error inside generator ->", type(e).__name__, e, "| context:", repr(e.__context__))
# TLS verification default
os.environ.pop("PYNNTP_TLS_INSECURE", None)
try:
    nntp.NNTPClient("localhost", 563, use_ssl=True).quit(); print("TLS w/o verify bypass: connected (!)")
except Exception as e:
    print("TLS default verify ->", type(e).__name__, str(e)[:120])
os.environ["PYNNTP_TLS_INSECURE"] = "0"
try:
    nntp.NNTPClient("localhost", 563, use_ssl=True).quit(); print("PYNNTP_TLS_INSECURE=0 -> verification DISABLED, connected")
except Exception as e:
    print("INSECURE=0 ->", type(e).__name__, e)
# STARTTLS: capabilities after TLS still list STARTTLS?
c = nntp.NNTPClient("localhost", use_ssl=True, ssl_mode=SSLMode.STARTTLS)
print("caps after STARTTLS+MODE READER:", [x for x in c.capabilities() if x.split()[0] in ("STARTTLS","READER","MODE-READER","AUTHINFO","COMPRESS")])
c.quit()
c = nntp.NNTPClient("localhost", use_ssl=True, ssl_mode=SSLMode.STARTTLS, reader=False)
print("caps after STARTTLS no MODE READER:", [x for x in c.capabilities() if x.split()[0] in ("STARTTLS","READER","MODE-READER","AUTHINFO","COMPRESS")])
c.quit()
