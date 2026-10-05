#!/usr/bin/env python3
"""Talks to the sys-remote sysmodule on the test Switch: banner, AUTH <token>, then one command per line.

Commands seen in the sysmodule: PING, FGAPP, PRESS <button> [n], TOUCH x y, SCREENSHOT, LAUNCH <tid>,
LAUNCHNRO <sd path>, KILL, STARTHBM, REBOOT, SHUTDOWN, QUIT.

Usage: swremote.py "<command>" [...]
       swremote.py --shot out.jpg
Token: SWREMOTE_TOKEN, else read from the console's sdmc:/config/sys-remote/config.ini over FTP.
"""
import os, socket, sys, time, urllib.request

HOST = os.environ.get('SWITCH_IP', '172.31.99.188')
PORT = int(os.environ.get('SWREMOTE_PORT', '7331'))


def token():
    t = os.environ.get('SWREMOTE_TOKEN')
    if t:
        return t
    for port in (os.environ.get('SWITCH_FTP_PORT', '5000'), '5002', '5000'):
        try:
            ini = urllib.request.urlopen(f'ftp://{HOST}:{port}/config/sys-remote/config.ini', timeout=15).read().decode()
            break
        except OSError:
            continue
    else:
        sys.exit('no FTP server to read the sys-remote token from')
    for line in ini.splitlines():
        if line.strip().startswith('token='):
            return line.split('=', 1)[1].strip()
    sys.exit('no token')


class Remote:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=30)
        self.f = self.s.makefile('rb')
        self.f.readline()                                   # HELLO sys-remote 1.0
        self.s.sendall(f'AUTH {token()}\n'.encode())
        r = self.f.readline()
        if not r.startswith(b'OK'):
            sys.exit(f'auth failed: {r!r}')

    def cmd(self, c):
        """Sends one command; returns (reply line, binary payload or None)."""
        self.s.sendall((c + '\n').encode())
        line = self.f.readline()
        p = line.split()
        if len(p) >= 2 and p[0] == b'OK' and p[1].isdigit() and int(p[1]) > 64 and c.upper().startswith('SCREENSHOT'):
            return line, self.f.read(int(p[1]))
        return line, None

    def close(self):
        try:
            self.s.sendall(b'QUIT\n')
        except OSError:
            pass
        self.s.close()


if __name__ == '__main__':
    r = Remote()
    args = sys.argv[1:]
    out = 'shot.jpg'
    if args and args[0] == '--shot':
        out, args = args[1], ['SCREENSHOT']
    for c in args:
        if c.startswith('sleep '):
            time.sleep(float(c.split()[1]))
            continue
        line, data = r.cmd(c)
        print(f'> {c}: {line.decode(errors="replace").rstrip()}')
        if data:
            open(out, 'wb').write(data)
            print(f'  {len(data)} bytes -> {out}')
    r.close()
