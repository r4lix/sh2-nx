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
CAVE_TEX_CLEAR = 0x401970       # ee.c: TexBufferASM
# EE TexPatch buffers, in guest memory between the image and the heap (0x2500000-0x10000000):
# 2x and 4x the largest texture file (22,380,640 bytes, sh2e/pic/map), as EE sizes them.
TEX_BUF1, TEX_BUF2, TEX_BUF3 = 0x04000000, 0x06B00000, 0x09600000


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

    # -- TexPatch (EnableTexAddrHack): texture load buffers moved to guest memory sized for the EE
    # HD textures (ee.c commits it at start). The original buffer is at 0x1DBC040.
    (CAVE_TEX_CLEAR, b'\xCC' * 4, b'\xC3\xCC\xCC\xCC', 'cave: texture buffer clear'),
    (0x401CC1, p32(0x1DBC040), p32(TEX_BUF1), 'texture buffer 1 (static)'),
    (0x44B99E, p32(0x1DBC040), p32(TEX_BUF1), 'texture buffer 1'),
    (0x496F87, bytes.fromhex('0500000800'), b'\xB8' + p32(TEX_BUF2), 'texture buffer 2 (add -> mov)'),
    (0x49B40A, bytes.fromhex('0500481000'), b'\xB8' + p32(TEX_BUF2), 'texture buffer 2 (add -> mov)'),
    (0x57E826, p32(0x1DBC040), p32(TEX_BUF3), 'lake UFO buffer'),
    (0x57E835, p32(0x1DBC040), p32(TEX_BUF3), 'lake UFO buffer'),
    (0x58C2F6, p32(0x1DBC040), p32(TEX_BUF3), 'hospital UFO buffer'),
    (0x58C305, p32(0x1DBC040), p32(TEX_BUF3), 'hospital UFO buffer'),
    (0x44A00D, call(0x44A00D, 0x448810), call(0x44A00D, CAVE_TEX_CLEAR), 'texture load: clear buffer after'),
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
