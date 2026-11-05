#!/bin/sh
# Set up Debian/Ubuntu's inn2 package for pynntp's integration tests.
# Run as root on a disposable test machine or CI runner only: it changes the
# INN configuration and /etc/hosts, and the tests post articles.
#
#   sudo sh tests/integration/inn2/setup.sh
#
# Result: innd on 119, nnrpd (TLS, self-signed) on 563, groups local.general
# and local.test, NEWNEWS allowed for localhost, no feeding peer for localhost
# (pynntp sends STARTTLS before MODE READER, so localhost must reach nnrpd, not
# innd). With PYNNTP_VENV=1 it also makes a venv with pytest in
# /root/pynntp-venv. Safe to run again.
set -eu
export DEBIAN_FRONTEND=noninteractive

# inn2's postinst fails if the hostname doesn't resolve (seen on Ubuntu 22.04).
if ! getent hosts "$(hostname)" >/dev/null; then
    echo "127.0.1.1 $(hostname).localdomain $(hostname)" >> /etc/hosts
fi

apt-get -qq update
ETC=/etc/news
# The postinst fails when the hostname has no domain part ("hostname does not
# resolve or domain not set in inn.conf", Ubuntu 22.04 containers). Then set
# domain: in inn.conf and finish the configuration.
if ! apt-get -qq install -y inn2 python3-venv openssl >/dev/null; then
    case "$(hostname -f 2>/dev/null)" in
    *.*) ;;
    *) grep -q '^domain:' $ETC/inn.conf || echo 'domain: localdomain' >> $ETC/inn.conf ;;
    esac
    dpkg --configure -a
    apt-get -qq install -y inn2 python3-venv openssl >/dev/null
fi
NEWSUSER=news

# Without a domain, INN 2.7 builds Message-IDs it then rejects itself
# ("441 Can't parse Message-ID header field body", Ubuntu 26.04).
case "$(hostname -f 2>/dev/null)" in
*.*) ;;
*) grep -q '^domain:' $ETC/inn.conf || echo 'domain: localdomain' >> $ETC/inn.conf ;;
esac

# localhost must not be a feeding peer; otherwise innd answers it.
if grep -q '^peer ME' $ETC/incoming.conf; then
    # comment out the whole "peer ME { ... }" block
    sed -i '/^peer ME/,/^}/ s/^/#pynntp# /' $ETC/incoming.conf
fi

# NEWNEWS for localhost readers: readers.conf needs the N permission;
# inn.conf's allownewnews alone isn't enough (found by pynntp-sol).
sed -i '/^access "localhost"/,/^}/ s/^\(\s*access:\s*\)RPA\s*$/\1RPAN/' $ETC/readers.conf

# TLS for nnrpd: self-signed certificate.
if [ ! -f $ETC/pynntp-cert.pem ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=localhost" \
        -keyout $ETC/pynntp-key.pem -out $ETC/pynntp-cert.pem 2>/dev/null
    chown $NEWSUSER:$NEWSUSER $ETC/pynntp-key.pem $ETC/pynntp-cert.pem
    chmod 600 $ETC/pynntp-key.pem
fi
for kv in "tlscertfile: $ETC/pynntp-cert.pem" "tlskeyfile: $ETC/pynntp-key.pem" "tlscapath: $ETC"; do
    key=${kv%%:*}
    if grep -q "^$key:" $ETC/inn.conf; then
        sed -i "s|^$key:.*|$kv|" $ETC/inn.conf
    else
        echo "$kv" >> $ETC/inn.conf
    fi
done

systemctl restart inn2 || systemctl start inn2
sleep 3

# The groups the tests post to (Debian's package usually has them already).
for g in local.general local.test; do
    if ! grep -q "^$g " /var/lib/news/active; then
        su -s /bin/sh $NEWSUSER -c "/usr/lib/news/bin/ctlinnd newgroup $g y pynntp"
    fi
done

# nnrpd with implicit TLS on 563, as a daemon (not managed by systemd).
# Restart it on every run: it reads inn.conf only at startup, and it names
# itself "nnrpd: accepting connections", so find it by its port.
for pid in $(ss -ltnpH 'sport = :563' | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
    kill "$pid" 2>/dev/null || true
done
sleep 1
/usr/lib/news/bin/nnrpd -D -p 563 -S

# Test runner venv, for test machines without one.
if [ "${PYNNTP_VENV:-0}" = 1 ] && [ ! -x /root/pynntp-venv/bin/pytest ]; then
    python3 -m venv /root/pynntp-venv
    /root/pynntp-venv/bin/pip -q install pytest
fi

sleep 1
ss -ltn | grep -E ':(119|563) ' || true
grep -E '^local\.' /var/lib/news/active || true
df -h / | tail -1
