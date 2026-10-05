#!/usr/bin/env python3
"""Lays out the SD card folder: <out>/switch/sh2-nx/ with the NRO, the exe, data/ and defaults.

Usage: make_sd.py <out dir> [--data <game data dir>] [--keyconf <keyconf.dat>] [--lang fr|en|de|it|es|jp]
Files already present and the same size are not copied again.
"""
import argparse, os, shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# DX_CONFIG_LANGUAGE as the game reads it from language.ini (it maps 0..5 onto j/e/f/g/i/s files):
# 0 -> Japanese, 1 -> German, 2 -> French, 3 -> Spanish, 4 -> Italian, 5 -> English.
LANG = {'jp': 0, 'de': 1, 'fr': 2, 'es': 3, 'it': 4, 'en': 5}


def copy(src, dst):
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--data', default=os.path.join(ROOT, 'game', 'data'))
    ap.add_argument('--keyconf')
    ap.add_argument('--lang', default='fr', choices=LANG)
    a = ap.parse_args()
    dst = os.path.join(a.out, 'switch', 'sh2-nx')
    n = copy(os.path.join(ROOT, 'build', 'switch', 'sh2-nx.nro'), os.path.join(dst, 'sh2-nx.nro'))
    n += copy(os.path.join(ROOT, 'game', 'sh2pc.exe'), os.path.join(dst, 'sh2pc.exe'))
    for dp, _, fs in os.walk(a.data):
        for f in fs:
            src = os.path.join(dp, f)
            n += copy(src, os.path.join(dst, 'data', os.path.relpath(src, a.data)))
    if a.keyconf:
        n += copy(a.keyconf, os.path.join(dst, 'keyconf.dat'))
    with open(os.path.join(dst, 'language.ini'), 'w', newline='\n') as f:
        f.write(f'SET DX_CONFIG_LANGUAGE {LANG[a.lang]}\n')
    print(f'{n} files copied to {dst} (language: {a.lang})')


if __name__ == '__main__':
    main()
