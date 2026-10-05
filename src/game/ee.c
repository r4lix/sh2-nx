/* Silent Hill 2 Enhancements (github.com/elishacloud/Silent-Hill-2-Enhancements, zlib license) ported
 * to the recompiled v1.0 executable. EE patches the game at run time from a d3d8.dll; here the code
 * patches are applied to the exe before recompilation (tools/patch_exe.py) and EE's hooks become the
 * functions below. A `sub_X` defined here replaces the generated one; `sub_X_gen` is the original,
 * which the recompiler emits under that name (regen.sh passes --exclude-manual for this file).
 *
 * Addresses are v1.0's, resolved from EE's search patterns by tools/eeaddr.py and tools/eepattern.py. */
#include "../runtime/rt.h"
#include <math.h>
#include <SDL2/SDL.h>

/* ---- game state (EE Patches/Common.cpp, Patches.h) ---- */
#define EE_ROOM_ID            0x01FB7DACu
#define EE_EVENT_INDEX        0x00932178u
#define EE_MENU_EVENT         0x00932174u
#define EE_TRANSITION_STATE   0x01F7D490u
#define EE_VIBRATION_LEVEL    0x01DBBFF9u  /* 0 off, 1 soft, 2 normal, 3 hard */
#define EE_RUMBLE_FLAG        0x00940EB6u
#define EE_GAMEPAD_TYPE       0x00941148u
enum { EVENT_IN_GAME = 4, R_NONE = 0, FADE_NONE = 0 };

/* ---- input (EE Patches/ControllerTweaks.cpp) ---- */
#define JOY_STATE        0x00940F20u  /* the game's DIJOYSTATE2 */
#define USING_GAMEPAD    0x01FB806Au
#define MOVE_DIRECTION   0x01FB7CE8u
#define STRAFING_LEFT    0x01FB7F26u
#define STRAFING_RIGHT   0x01FB7F27u

/* EE settings, as the Enhanced Edition ships them (d3d8.ini). */
static const int DPadMovementFix = 1;           /* DPAD_MOVEMENT_MODE: the d-pad moves like the stick */
static const int RestoreSearchCamMovement = 2;  /* right stick (Z / Rz) drives the search camera */

static int is_moving_around(void) {
    return MEM8(USING_GAMEPAD) || MEM8(STRAFING_LEFT) || MEM8(STRAFING_RIGHT);
}

/* ProcessDInputData(GamePadState *state): the game turning the polled DIJOYSTATE2 into its pad
 * state. EE's hook runs first: d-pad movement, then the right stick into state->m_rightStick. */
extern void sub_00458060_gen(void);
void sub_00458060(void) {
    uint32_t state = MEM32(g_esp + 4);
    uint32_t pov = MEM32(JOY_STATE + 32);
    if (DPadMovementFix && (pov & 0xFFFF) != 0xFFFF) {
        double a = (double)pov * M_PI / (180.0 * 100.0);
        MEM32(JOY_STATE + 0) = (uint32_t)(int32_t)(sin(a) * 32767.0);   /* lX */
        MEM32(JOY_STATE + 4) = (uint32_t)(int32_t)(cos(a) * -32767.0);  /* lY */
    }
    if (RestoreSearchCamMovement == 2) {
        *(int16_t *)GPTR(state + 0xC) = (int16_t)(int32_t)MEM32(JOY_STATE + 8);   /* lZ */
        *(int16_t *)GPTR(state + 0xE) = (int16_t)(int32_t)MEM32(JOY_STATE + 20);  /* lRz */
    }
    sub_00458060_gen();
}

/* UsingSearchCamera, as EE's UsingSearchCamera_SeparateAnalogs at the nine walking call sites EE
 * patches: walking and looking around at the same time. The two other callers keep the original. */
extern void sub_00534660_gen(void);
void sub_00534660(void) {
    uint32_t ret = MEM32(g_esp);
    if (ret != 0x0051EC65u && ret != 0x00547FFFu && is_moving_around()) {
        g_eax = 0;
        g_esp += 4;
        return;
    }
    sub_00534660_gen();
}

/* Cave 0x401460, called from 0x535CBD: EE's StartSearchCamera_Hook (TRUE: do not start it). */
void sub_00401460(void) {
    uint32_t dir = MEM32(MOVE_DIRECTION);
    g_eax = is_moving_around() ? 0 : (dir != 0 && dir != 3);
    g_esp += 4;
}

/* Cave 0x4015D0, called from 0x4697B5 (`mov eax, 10h` before the event index is stored): EE's
 * PauseScreenASM, leaving Options from the pause screen straight back to gameplay. */
void sub_004015D0(void) {
    guest_call(0x0047EEE0u, 0, NULL, 0);  /* fixes doubled text */
    guest_call(0x0046AB10u, 0, NULL, 0);  /* the call used when returning to gameplay */
    guest_call(0x00401032u, 0, NULL, 0);  /* fixes incorrect text */
    g_eax = 2;
    g_esp += 4;
}

/* ---- vibration (EE Wrappers/dinput8/IDirectInputEffect.cpp, RestoreVibration) ---- */

/* CreateDirectInputGamepad: a pad that created an effect is driven as a rumble pad (type 2). */
extern void sub_00458760_gen(void);
void sub_00458760(void) {
    sub_00458760_gen();
    if (MEM32(EE_GAMEPAD_TYPE) != 0) MEM32(EE_GAMEPAD_TYPE) = 2;
}

/* Strength follows the game's own Vibration option. Called by the DirectInput effect bridge. */
uint32_t ee_rumble_gain(uint32_t magnitude) {
    uint8_t level = MEM8(EE_VIBRATION_LEVEL);
    if (level >= 3) return magnitude ? 10000 : 0;
    return magnitude ? 10000u * level / 3u : 0;
}

void dinput_rumble_stop(void);

/* recomp_lookup_manual: every call the recompiler routed through the manual table lands here. */
recomp_func_t ee_lookup_manual(uint32_t va) {
    switch (va) {
    case 0x00458060u: return sub_00458060;
    case 0x00534660u: return sub_00534660;
    case 0x00458760u: return sub_00458760;
    case 0x00401460u: return sub_00401460;
    case 0x004015D0u: return sub_004015D0;
    }
    return NULL;
}

/* Once per presented frame: no rumble outside gameplay, in a fade or between rooms (EE's
 * RunInfiniteRumbleFix). */
void ee_frame(void) {
    static int blocked;
    int block = MEM8(EE_EVENT_INDEX) != EVENT_IN_GAME || MEM32(EE_ROOM_ID) == R_NONE ||
                MEM32(EE_TRANSITION_STATE) != FADE_NONE;
    if (block && !blocked) {
        MEM8(EE_RUMBLE_FLAG) = 0;
        if (MEM32(EE_TRANSITION_STATE) != FADE_NONE) dinput_rumble_stop();
    } else if (!block && blocked)
        MEM8(EE_RUMBLE_FLAG) = 1;
    blocked = block;
}
