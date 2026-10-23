"""Tiny scripted NNTP server to probe pynntp client paths (no INN)."""
import socket, threading, sys, zlib, gzip, warnings, gc, time, binascii
sys.path.insert(0, sys.argv[1])
import nntp

def serve(handler):
    ls = socket.socket(); ls.bind(("127.0.0.1", 0)); ls.listen(5)
    port = ls.getsockname()[1]
    def loop():
        while True:
            try: s, _ = ls.accept()
            except OSError: return
            threading.Thread(target=handler, args=(s,), daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()
    return port, ls

def lines(s):
    f = s.makefile("rb")
    while True:
        l = f.readline()
        if not l: return
        yield l.rstrip(b"\r\n").decode()

def run(name, fn):
    try: print(f"{name}: -> {fn()!r}"[:400])
    except BaseException as e: print(f"{name}: !! {type(e).__name__} {str(e)[:200]}")

log = []
# 1/2: auth flows
def auth_server(always480):
    def h(s):
        s.sendall(b"200 hi\r\n")
        authed = False
        for l in lines(s):
            log.append(l)
            if l.startswith("MODE READER"): s.sendall(b"200 ok\r\n")
            elif l.startswith("AUTHINFO USER"): s.sendall(b"381 pass\r\n" if l != "AUTHINFO USER" else b"501 syntax\r\n")
            elif l.startswith("AUTHINFO PASS"): authed = True; s.sendall(b"281 ok\r\n")
            elif l.startswith("GROUP"):
                s.sendall(b"480 auth\r\n" if (always480 or not authed) else b"211 1 1 1 g\r\n")
            elif l == "QUIT": s.sendall(b"205 bye\r\n"); return
            else: s.sendall(b"500 what\r\n")
    return h
p, _ = serve(auth_server(False))
c = nntp.NNTPClient("127.0.0.1", p)
log.clear(); run("480 with no credentials", lambda: c.group("g")); print("   sent:", log)
c = nntp.NNTPClient("127.0.0.1", p, "u", "pw")
log.clear(); run("480 with credentials", lambda: c.group("g")); print("   sent:", log)
p, _ = serve(auth_server(True))
c = nntp.NNTPClient("127.0.0.1", p, "u", "pw", timeout=3)
log.clear(); run("server keeps answering 480 after 281", lambda: c.group("g")); print("   commands sent:", len(log))

# 3: gzip + dot-stuffed line
def gz_server(s):
    s.sendall(b"200 hi\r\n")
    for l in lines(s):
        if l.startswith("MODE"): s.sendall(b"200 ok\r\n")
        elif l.startswith("XOVER"):
            payload = b"1\tsubj\tfrom\tdate\t<a@b>\t\t10\t1\r\n..dot\r\n.\r\n"
            s.sendall(b"224 data follows [COMPRESS=GZIP]\r\n" + gzip.compress(payload) )
            time.sleep(0.2); s.sendall(b"")
        elif l.startswith("BODY"):
            s.sendall(b"222 0 <a@b> body\r\n" + BODY + b".\r\n")
        elif l == "QUIT": s.sendall(b"205 bye\r\n"); return
p, _ = serve(gz_server)
c = nntp.NNTPClient("127.0.0.1", p)
run("gzip info with dot-stuffed line (raw _info lines)", lambda: list(c._info_gzip.__self__._info(224, "[COMPRESS=GZIP]")) if c.socket.sendall(b"XOVER\r\n") or c.status() else None)

# 4: yEnc multi-part body where an encoded line starts with '.'
data = bytes(range(256)) * 4
data = bytes(4 if i % 128 == 0 else b for i, b in enumerate(data))
def yenc_encode(data, linelen=128):
    out, line = [], bytearray()
    for i, b in enumerate(data):
        e = (b + 42) & 0xFF
        if e in (0, 10, 13, 61): line += b"=" + bytes([(e + 64) & 0xFF])
        else: line.append(e)
        if len(line) >= linelen: out.append(bytes(line)); line = bytearray()
    if line: out.append(bytes(line))
    return out
enc = yenc_encode(data)
# make sure at least one line starts with '.' (0x2E = 4+42): force by prepending
dotted = [l for l in enc if l.startswith(b".")]
crc = binascii.crc32(data) & 0xFFFFFFFF
body = [b"=ybegin part=1 total=1 line=128 size=%d name=x.bin" % len(data), b"=ypart begin=1 end=%d" % len(data)] + enc + [b"=yend size=%d part=1 pcrc32=%08x" % (len(data), crc)]
BODY = b"".join((b"." + l if l.startswith(b".") else l) + b"\r\n" for l in body)
print("encoded lines starting with '.':", len(dotted))
run("yEnc body decoded == original", lambda: (lambda d: (d == data, len(d), len(data)))(c.body("<a@b>")))

# 5: greeting 502 / STARTTLS 580 leak; timeout class
def bad_greet(s): s.sendall(b"502 go away\r\n"); time.sleep(0.5)
p, _ = serve(bad_greet)
warnings.simplefilter("always", ResourceWarning)
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    run("greeting 502", lambda: nntp.NNTPClient("127.0.0.1", p)); gc.collect()
print("   ResourceWarning on greeting failure:", "ResourceWarning" in buf.getvalue())
def silent(s): s.sendall(b"200 hi\r\n"); time.sleep(5)
p, _ = serve(silent)
run("server never answers MODE READER (timeout=1)", lambda: nntp.NNTPClient("127.0.0.1", p, timeout=1))
print("   is TimeoutError an NNTPError?", issubclass(TimeoutError, nntp.NNTPError))
def starttls_fail(s):
    s.sendall(b"200 hi\r\n")
    for l in lines(s):
        s.sendall(b"580 can not initiate TLS\r\n")
p, _ = serve(starttls_fail)
from nntp.types import SSLMode
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    run("STARTTLS 580", lambda: nntp.NNTPClient("127.0.0.1", p, use_ssl=True, ssl_mode=SSLMode.STARTTLS)); gc.collect()
print("   ResourceWarning on STARTTLS failure:", "ResourceWarning" in buf.getvalue())
# 6: date format sent by newgroups
def cap(s):
    s.sendall(b"200 hi\r\n")
    for l in lines(s):
        log.append(l)
        if l.startswith("MODE"): s.sendall(b"200 ok\r\n")
        elif l.startswith("NEW"): s.sendall(b"231 ok\r\n.\r\n" if l.startswith("NEWG") else b"230 ok\r\n.\r\n")
        elif l.startswith("XHDR"): s.sendall(b"221 ok\r\n<a@b> subj\r\n.\r\n")
        elif l.startswith("HDR"): s.sendall(b"225 ok\r\n0 subj\r\n.\r\n")
        else: s.sendall(b"500 x\r\n")
p, _ = serve(cap)
from datetime import datetime, timezone
c = nntp.NNTPClient("127.0.0.1", p)
log.clear(); list(c.newgroups(datetime(2024,1,2,3,4,5))); list(c.newnews("a.*", datetime(2024,1,2,3,4,5,tzinfo=timezone.utc))); print("sent:", log)
log.clear(); run("command with CRLF in arg", lambda: c.command("GROUP", "a\r\nPOST")); print("  server received:", log)
