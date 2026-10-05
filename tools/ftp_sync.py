#!/usr/bin/env python3
"""Uploads files to the Switch over FTP (sys-ftpd) with curl, skipping ones already there with the same size.

sys-ftpd crashes (taking an Atmosphere crash screen with it) on commands it does not implement, such
as MLSD or MKD of an existing directory, so this only drives curl, whose LIST/CWD/STOR sequence is
known to work: one curl per directory, files sent over one connection, directories created only when
CWD fails (--ftp-create-dirs).

Usage: ftp_sync.py <local file or dir> <remote dir> [...pairs]
"""
import os, subprocess, sys, time

HOST = os.environ.get('SWITCH_IP', '172.31.99.188')
PORT = int(os.environ.get('SWITCH_FTP_PORT', '5000'))
URL = f'ftp://{HOST}:{PORT}'


def remote_sizes(d):
    r = subprocess.run(['curl', '-s', '--max-time', '60', f'{URL}{d}/'], capture_output=True, text=True)
    out = {}
    for l in r.stdout.splitlines():
        p = l.split(None, 8)
        if len(p) == 9:
            out[p[8]] = -2 if l.startswith('d') else int(p[4])
    return out


def upload_dir_batch(rd, files):
    """files: local paths, all going to remote dir rd."""
    have = remote_sizes(rd)
    todo = [f for f in files if have.get(os.path.basename(f)) != os.path.getsize(f)]
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        for attempt in range(3):
            args = ['curl', '-s', '-S', '--ftp-create-dirs', '--retry', '2']
            for f in chunk:
                args += ['-T', f, f'{URL}{rd}/{os.path.basename(f)}']
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode == 0:
                break
            print(f'  retry {rd}: {r.stderr.strip()}', flush=True)
            time.sleep(5)
        else:
            sys.exit(f'upload to {rd} failed')
    return todo


if __name__ == '__main__':
    args = sys.argv[1:]
    t0, total, n = time.time(), 0, 0
    groups = {}
    for i in range(0, len(args), 2):
        local, rd = args[i], args[i + 1].rstrip('/')
        if os.path.isdir(local):
            for dp, _, fs in os.walk(local):
                rel = os.path.relpath(dp, local).replace('\\', '/')
                key = rd if rel == '.' else f'{rd}/{rel}'
                groups.setdefault(key, []).extend(os.path.join(dp, f) for f in sorted(fs))
        else:
            groups.setdefault(rd, []).append(local)
    for rd in sorted(groups):
        sent = upload_dir_batch(rd, groups[rd])
        n += len(sent)
        total += sum(os.path.getsize(f) for f in sent)
        if sent:
            print(f'{n:5} files {total >> 20:6} MB  {rd}', flush=True)
    print(f'done in {time.time() - t0:.0f}s: {n} files, {total >> 20} MB', flush=True)
