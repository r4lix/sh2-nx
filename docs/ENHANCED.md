# Silent Hill 2: Enhanced Edition on Switch (fork notes)

This fork targets the **unprotected v1.0 `sh2pc.exe` shipped with the Enhanced Edition package**
(5,459,968 bytes, SHA-1 `3d7e1161772e0a39cb9d57d92cfaf8b5e4871b04`) instead of the 5,685,248-byte exe
upstream expects. The upstream pipeline's hard-coded addresses (setjmp/longjmp thunks, seeds) already
match this exe byte for byte.

## Building on Windows (no podman)

```sh
py -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
# .venv/bin/python3 must exist for tools/regen.sh: a two-line sh shim calling ../Scripts/python.exe
sh tools/regen.sh                 # patches the exe (tools/patch_exe.py), then recompiles (~5 min)
sh tools/build-switch-local.sh    # devkitA64 + switch-sdl2, switch-mesa, switch-ffmpeg, switch-pkg-config
python tools/make_sd.py <SD root> --data <game>/data --keyconf <EE>/keyconf.dat --lang fr
```

## What changed

### Language
`language.ini` next to the NRO: `SET DX_CONFIG_LANGUAGE n`. The game maps n onto its message files
(0 j, 1 g, 2 f, 3 s, 4 i, 5 e): **2 = French**. `tools/make_sd.py --lang fr` writes it.

### Controller (`src/win32/dinput.c`, `src/game/ee.c`)
- DirectInput force feedback implemented (constant/ramp/periodic effects) and sent to the pad with
  `SDL_GameControllerRumble` (Switch HD rumble), scaled by the in-game Vibration option.
- EE ControllerTweaks: d-pad movement, right stick drives the search camera
  (`RestoreSearchCamMovement = 2`), walking while looking around.
- EE vibration fixes: no rumble outside gameplay / during fades, main-menu infinite rumble removed.
- `keyconf.dat` from the Enhanced Edition is used as the default button layout.

### Enhanced Edition patches
EE patches the running game from its d3d8.dll. Here:
- code byte patches are applied to the exe before recompilation (`tools/patch_exe.py`, each site
  verified against the original bytes);
- hooks become hand-written functions in `src/game/ee.c`: a `sub_X` there replaces the generated one,
  and `extern void sub_X_gen(void)` keeps the original body callable. `regen.sh` passes
  `--exclude-manual src/game/ee.c`; calls to wrapped functions route through `recomp_lookup_manual`
  (xboxrecomp change: `translate_batch_split(wrapped=...)`).
- new code needs an address: int3 padding between functions is turned into `ret` "caves" that the
  patched code calls and `ee.c` defines.
- `tools/eepattern.py` / `tools/eeaddr.py` resolve EE's search patterns to v1.0 addresses.

Ported so far: ControllerTweaks (search camera, d-pad, separate analogs), RestoreVibration,
PauseScreenFix.

### Upstream issues
- **Missing branch in MSVC switch chains** (xboxrecomp lifter): a jcc reached by both `cmp` and
  `sub`/`add`/`inc`/`dec` edges had no single flag snapshot and lifted as the never-true `_flags`
  fallback. Every ZF producer now also writes `_zr` (zero iff ZF), and mixed joins read it
  (`test_flag_join_switch_chain.py`). `prefetch*`/`lfence`/`mfence` no longer drop flag tracking.
  `tools/flagchains.py` lists what is left: 3DNow! paths (never taken: the runtime reports no
  3DNow!) and data decoded as code.
- **Stutter when areas or shaders load**: programs were compiled at first draw. Every program key is
  now appended to `sh2-progs.bin` (shaders identified by a hash of their GLSL) and rebuilt at the
  next start: fixed-function ones before the first draw, shader ones once the game created them.
- **Pause background not frozen in some rooms**: needs hardware testing.

## Status 2026-10-05 and next steps (EE assets)

- Director's Cut boots on hardware (title menu reached). Main-menu images are English/Japanese only in
  DC data (pic/etc/start00/01); French text is in-game. Mouse cursor (knife) is drawn: report no mouse.
- EE file redirection (EE Common/FileSystemHooks.cpp): `data/X` is loaded from `sh2e/X` when it exists
  (end.bik/ending.bik and start01 need start00 special cases). To do in `rt_path` with per-folder switches.
- sh2e sizes: movie 4.9 GB, sound 4.0 GB, pic 1.9 GB (281 files, 56 over 16 MB = 1.1 GB, up to 21 MB
  e.g. pic/map/*.tex), bg 117 MB, menu 11 MB, font 16 MB.
- HD textures need EE PatchTexAddr (TexPatch.cpp): texture load buffers at 0x401CC1 / 0x44B99D /
  0x496F87 / 0x49B40A (+ UFO 0x57E84E-0x28, 0x58C31E-0x28) moved to larger buffers. Port plan: reserve
  fixed guest VAs for the buffers, patch the immediates in tools/patch_exe.py, clear hook as an ee.c cave.
- Audio pack needs EE PatchCriware/SfxPatch (BGM size tables) before sh2e/sound can be used.
- sys-ftpd moved to port 5002 (config.ini.bak kept); sphaira FTP on 5000 is faster. Use curl only
  (tools/ftp_sync.py): sys-ftpd crashes on MLSD and on MKD of an existing directory.
