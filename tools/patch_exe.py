#!/usr/bin/env python3
"""Applies the Silent Hill 2 Enhancements code patches to sh2pc.exe (v1.0) before recompilation.

Recompiled code is static C, so EE's run-time code patches have to happen to the bytes the
recompiler reads. Patches that need new code call a "cave" (int3 padding between functions, given a
`ret` here) that src/game/ee.c defines by hand. Every site is verified against the original bytes.

Usage: patch_exe.py game/sh2pc.exe build/sh2pc_ee.exe
"""
import struct, sys

BASE = 0x400000
CAVE_SEARCH_CAMERA = 0x401460   # ee.c: StartSearchCamera_Hook
CAVE_PAUSE_OPTIONS = 0x4015D0   # ee.c: PauseScreenASM


def call(at, target):
    return b'\xE8' + struct.pack('<i', target - (at + 5))


def p32(v):
    return struct.pack('<I', v)


# (va, expected original bytes, replacement, why)
PATCHES = [
    # -- caves: int3 padding becomes `ret` so the disassembler sees a function there
    (CAVE_SEARCH_CAMERA, b'\xCC' * 4, b'\xC3\xCC\xCC\xCC', 'cave: search camera hook'),
    (CAVE_PAUSE_OPTIONS, b'\xCC' * 4, b'\xC3\xCC\xCC\xCC', 'cave: pause options exit'),

    # -- ControllerTweaks (RestoreSearchCamMovement): the search camera reads the right stick
    (0x535CD1, p32(0x1FB8054), p32(0x1FB804C), 'search camera X <- right stick X'),
    (0x535D53, p32(0x1FB8054), p32(0x1FB804C), 'search camera X <- right stick X'),
    (0x535CE4, p32(0x1FB8058), p32(0x1FB8050), 'search camera Y <- right stick Y'),
    (0x535D6B, p32(0x1FB8058), p32(0x1FB8050), 'search camera Y <- right stick Y'),
    # StartSearchCamera_Hook: `mov eax, [moveDirection]` -> call; keep `test eax, eax`; drop `je; cmp`
    (0x535CBD, bytes.fromhex('a1e87cfb01'), call(0x535CBD, CAVE_SEARCH_CAMERA), 'start search camera hook'),
    (0x535CC4, bytes.fromhex('740983f803'), b'\x90' * 5, 'start search camera hook'),

    # -- PauseScreen fix: leaving Options from the pause menu returns to gameplay cleanly
    (0x4697B5, bytes.fromhex('b810000000'), call(0x4697B5, CAVE_PAUSE_OPTIONS), 'pause screen options exit'),

    # -- XInput vibration: the main menu's rumble call never stops (infinite rumble)
    (0x497D71, bytes.fromhex('e8ba05fcff'), b'\x90' * 5, 'menu infinite rumble'),
]


def main(src, dst):
    data = bytearray(open(src, 'rb').read())
    for va, old, new, why in PATCHES:
        o = va - BASE
        if data[o:o + len(old)] != old:
            sys.exit(f'{va:#x} ({why}): expected {old.hex()} found {data[o:o + len(old)].hex()}')
        data[o:o + len(new)] = new
    open(dst, 'wb').write(data)
    print(f'{len(PATCHES)} patches -> {dst}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
