#!/usr/bin/env python3
"""Uploads files to the Switch over FTP (sys-ftpd), skipping ones already there with the same size.

Usage: ftp_sync.py <local file or dir> <remote dir> [...pairs]
       e.g. ftp_sync.py ../original-dc/data /switch/sh2-nx/data build/switch/sh2-nx.nro /switch/sh2-nx
"""
import ftplib, os, sys, time

HOST = os.environ.get('SWITCH_IP', '172.31.99.188')
PORT = int(os.environ.get('SWITCH_FTP_PORT', '5000'))


def connect():
    f = ftplib.FTP()
    f.connect(HOST, PORT, timeout=60)
    f.login()
    f.set_pasv(True)
    return f


def remote_sizes(f, d):
    out = {}
    try:
        for name, facts in f.mlsd(d, facts=['size', 'type']):
            out[name] = int(facts.get('size', -1)) if facts.get('type') == 'file' else -2
    except ftplib.all_errors:
        try:
            lines = []
            f.retrlines(f'LIST {d}', lines.append)
            for l in lines:
                p = l.split(None, 8)
                if len(p) == 9:
                    out[p[8]] = -2 if l.startswith('d') else int(p[4])
        except ftplib.all_errors:
            pass
    return out


def mkdirs(f, d, known):
    parts = d.strip('/').split('/')
    for i in range(1, len(parts) + 1):
        p = '/' + '/'.join(parts[:i])
        if p in known:
            continue
        try:
            f.cwd(p)          # sys-ftpd drops the connection on MKD of an existing directory
        except ftplib.error_perm:
            f.mkd(p)
        known.add(p)
    f.cwd('/')


def upload(f, local, remote_dir, state):
    files = []
    if os.path.isdir(local):
        for dp, _, fs in os.walk(local):
            for n in fs:
                src = os.path.join(dp, n)
                rel = os.path.relpath(dp, local).replace('\\', '/')
                files.append((src, remote_dir if rel == '.' else f'{remote_dir}/{rel}'))
    else:
        files.append((local, remote_dir))
    for src, rd in files:
        if rd not in state['listed']:
            mkdirs(f, rd, state['dirs'])
            state['listed'][rd] = remote_sizes(f, rd)
        name, size = os.path.basename(src), os.path.getsize(src)
        if state['listed'][rd].get(name) == size:
            continue
        with open(src, 'rb') as fh:
            f.storbinary(f'STOR {rd}/{name}', fh, blocksize=1 << 20)
        state['bytes'] += size
        state['n'] += 1
        print(f'{state["n"]:5} {state["bytes"] >> 20:6} MB  {rd}/{name}', flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    t0 = time.time()
    for attempt in range(5):
        state = {'listed': {}, 'dirs': set(), 'bytes': 0, 'n': 0}
        try:
            f = connect()
            for i in range(0, len(args), 2):
                upload(f, args[i], args[i + 1].rstrip('/'), state)
            f.quit()
            break
        except ftplib.all_errors + (EOFError,) as e:
            print(f'connection lost ({e}); retrying', flush=True)
            time.sleep(5)
    print(f'done in {time.time() - t0:.0f}s', flush=True)
