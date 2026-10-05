// steam_input.h — Steam Input activation for SteamLite (agent p7, 2026-10-04).
//
// The genuine client's controller manager (Steam Input) only configures a game's layout when the
// Steam UI tells it to. Headless, nobody does — so games that read the pad through the Steam Input
// API (ISteamInput / ISteamController: No Man's Sky, most newer Valve-published titles) see no
// controller at all under SteamLite, while XInput/DirectInput games are unaffected.
//
// This module does what the UI would: after logon and BEFORE LaunchApp it
//   1. makes sure SDL3's joystick+gamepad subsystems are up in the client (the client loads SDL3.dll
//      from its own dir; headless it never initialises the joystick side),
//   2. asks IClientEngine for IClientControllerSerialized and pins its vftable to a client build whose
//      slot layout was read from the binary (never call into an unknown layout),
//   3. EnableDeviceCallbacks(appid) + EnumerateControllers, waits briefly for a pad to appear,
//   4. LoadConfigFromVDFString(appid, <layout vdf the app chose>) + ActivateConfig(appid),
//   5. re-activates on SteamInputDeviceConnected_t (2801) / GamepadSlotChange_t (2804) while the game runs.
//
// Everything is gated on WN_STEAM_INPUT=1 (per-game toggle in the app). With the toggle off this
// header is inert: no interface is fetched, nothing is called. Any failure logs and gives up — it can
// never block or fail a launch.
//
// Slot numbers were recovered from steamclient64.dll's own IPC dispatcher for the serialized
// interface (each case ends in the virtual call it dispatches to) and cross-checked against a second
// client build; see docs/STEAMLITE_STEAM_INPUT.md in the Bannerlator repo.
//
// Env:
//   WN_STEAM_INPUT=1                    enable
//   WN_STEAM_INPUT_VDF=<win path>       controller_mappings VDF to load for the app (optional; without
//                                       it the client's own choice — usually nothing — is activated)
//   WN_STEAM_INPUT_UNPINNED=1           drive an unknown client build with the pinned slot table
#pragma once
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>

#if defined(_WIN64)
#define SI_THISCALL
#else
#define SI_THISCALL __thiscall
#endif

namespace si {

typedef void (*log_fn_t)(const char* fmt, ...);

// ── vftable slots ──────────────────────────────────────────────────────────────────────────────
static const int kVtEngine_GetIClientControllerSerialized = 66;   // IClientEngine (hUser, hPipe)
static const int kVtCtrl_EnableDeviceCallbacks            = 10;   // (appid, 0)
static const int kVtCtrl_GetNumConnectedControllers       = 22;   // ()
static const int kVtCtrl_LoadConfigFromVDFString          = 38;   // (0, appid, vdf, 0, 0)
static const int kVtCtrl_ActivateConfig                   = 40;   // (0, appid, true)
static const int kVtCtrl_EnumerateControllers             = 102;  // (0, 0)

// Vftable RVAs the pin accepts. In-process callers (us) get the client's own proxy class
// `IClientControllerSerializedMap` (each slot serialises the call into a message for the controller
// thread); its vftable has the interface's slot order (157 entries = 2 + the 155 named methods).
// `CSteamControllerSerialized` is the implementation behind it. Both read off the same build.
static const uintptr_t kKnownVftRva[] = {
    0x12f2360,   // IClientControllerSerializedMap — steamclient64.dll 10.52.09.55 (linked 2026-03-13), the SteamLite package build (device-observed)
    0x13172b8,   // CSteamControllerSerialized   — same build
};

static const int kCbSteamInputDeviceConnected     = 2801;
static const int kCbSteamInputDeviceDisconnected  = 2802;
static const int kCbSteamInputConfigurationLoaded = 2803;
static const int kCbSteamInputGamepadSlotChange   = 2804;

// ── state ──────────────────────────────────────────────────────────────────────────────────────
static log_fn_t    g_log = NULL;
static bool        g_enabled = false;
static std::string g_vdfPath;
static std::string g_vdf;
static void*       g_ctrl = NULL;        // IClientControllerSerialized*, only once pinned
static uint32_t    g_appId = 0;
static int         g_reactivations = 0;
static DWORD       g_activatedAt = 0;
static DWORD       g_lastPoll = 0;
static int         g_lastCount = -1;

static void logf(const char* fmt, ...) {
    if (!g_log) return;
    char buf[1024];
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    g_log("[wn-launcher] steam input: %s", buf);
}

static bool read_file(const char* path, std::string& out) {
    FILE* f = fopen(path, "rb");
    if (!f) return false;
    out.clear();
    char buf[8192]; size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) out.append(buf, n);
    fclose(f);
    return !out.empty();
}

static void init_from_env(log_fn_t log) {
    g_log = log;
    const char* on = getenv("WN_STEAM_INPUT");
    g_enabled = on && *on && strcmp(on, "0") != 0;
    const char* p = getenv("WN_STEAM_INPUT_VDF");
    if (p && *p) g_vdfPath = p;
    if (g_enabled)
        logf("enabled (layout=%s)", g_vdfPath.empty() ? "<client default>" : g_vdfPath.c_str());
}

static bool enabled() { return g_enabled; }
static bool active()  { return g_ctrl != NULL; }

// SDL3 joystick|gamepad up inside the client. The client loads SDL3.dll itself from the Steam dir
// when its controller code first runs; if it has not yet, load the same file so the enumeration
// below has a backend. SDL3's SDL_InitSubSystem returns bool.
static bool sdl_ensure() {
    const uint32_t kJoystick = 0x200u, kGamepad = 0x2000u;
    HMODULE sdl = GetModuleHandleA("SDL3.dll");
    const char* how = "already loaded by the client";
    if (!sdl) {
        sdl = LoadLibraryA("C:\\Program Files (x86)\\Steam\\SDL3.dll");
        how = "loaded from the Steam dir";
    }
    if (!sdl) {
        logf("SDL3.dll not available (err=%lu) — the SteamLite package must ship it next to steamclient64.dll",
             (unsigned long) GetLastError());
        return false;
    }
    typedef uint32_t    (*WasInitFn)(uint32_t);
    typedef bool        (*InitSubFn)(uint32_t);
    typedef const char* (*GetErrFn)(void);
    WasInitFn wasInit = (WasInitFn) GetProcAddress(sdl, "SDL_WasInit");
    InitSubFn initSub = (InitSubFn) GetProcAddress(sdl, "SDL_InitSubSystem");
    GetErrFn  getErr  = (GetErrFn)  GetProcAddress(sdl, "SDL_GetError");
    if (!wasInit || !initSub) {
        logf("SDL3.dll has no SDL_WasInit/SDL_InitSubSystem (%p/%p)", (void*) wasInit, (void*) initSub);
        return false;
    }
    uint32_t was = wasInit(kJoystick | kGamepad);
    if ((was & (kJoystick | kGamepad)) == (kJoystick | kGamepad)) {
        logf("SDL joystick subsystem already up (0x%x, %s)", was, how);
        return true;
    }
    bool ok = initSub(kJoystick | kGamepad);
    logf("SDL_InitSubSystem(joystick|gamepad) -> %d err=\"%s\" (was 0x%x, SDL3 %s)",
         ok ? 1 : 0, ok ? "" : (getErr ? getErr() : "?"), was, how);
    return ok;
}

static int num_controllers() {
    if (!g_ctrl) return -1;
    void** vt = *(void***) g_ctrl;
    typedef int (SI_THISCALL *NumFn)(void* self);
    return ((NumFn) vt[kVtCtrl_GetNumConnectedControllers])(g_ctrl);
}

static void load_and_activate(const char* why) {
    if (!g_ctrl) return;
    void** vt = *(void***) g_ctrl;
    if (!g_vdf.empty()) {
        typedef uint64_t (SI_THISCALL *LoadFn)(void* self, uint32_t zero, uint32_t appId,
                                               const char* vdf, uint64_t a, uint64_t b);
        ((LoadFn) vt[kVtCtrl_LoadConfigFromVDFString])(g_ctrl, 0, g_appId, g_vdf.c_str(), 0, 0);
        logf("LoadConfigFromVDFString(0, %u, %u bytes) done (%s)", g_appId, (unsigned) g_vdf.size(), why);
    }
    typedef uint64_t (SI_THISCALL *ActivateFn)(void* self, uint32_t zero, uint32_t appId, bool b);
    ((ActivateFn) vt[kVtCtrl_ActivateConfig])(g_ctrl, 0, g_appId, true);
    logf("ActivateConfig(0, %u, true) done (%s)", g_appId, why);
    g_activatedAt = GetTickCount();
}

// After logon, before LaunchApp. `engine` = IClientEngine*, (hUser, pipe) = the agent's global user.
static void activate(void* engine, int hUser, int pipe, uint32_t appId) {
    if (!g_enabled || !engine || appId == 0 || g_ctrl) return;
    g_appId = appId;
    if (!g_vdfPath.empty() && !read_file(g_vdfPath.c_str(), g_vdf)) {
        logf("layout %s unreadable — activating without a layout", g_vdfPath.c_str());
        g_vdf.clear();
    }

    void** engine_vt = *(void***) engine;
    typedef void* (SI_THISCALL *GetCtrlFn)(void* self, int hUser, int hPipe);
    void* ctrl = ((GetCtrlFn) engine_vt[kVtEngine_GetIClientControllerSerialized])(engine, hUser, pipe);
    if (!ctrl) { logf("GetIClientControllerSerialized -> NULL — not activating"); return; }

    // Pin: the object's vftable must belong to a client build whose slots we read off the binary.
    HMODULE   lsc = GetModuleHandleA("steamclient64.dll");
    uintptr_t vft = (uintptr_t) *(void**) ctrl;
    uintptr_t rva = lsc ? vft - (uintptr_t) lsc : 0;
    bool known = false;
    for (size_t i = 0; i < sizeof kKnownVftRva / sizeof kKnownVftRva[0]; ++i)
        if (rva == kKnownVftRva[i]) known = true;
    const char* unp = getenv("WN_STEAM_INPUT_UNPINNED");
    bool forced = unp && *unp && strcmp(unp, "0") != 0;
    if (!known && !forced) {
        logf("IClientControllerSerialized=%p vtable rva=%llx is not a pinned client build — "
             "skipping Steam Input (WN_STEAM_INPUT_UNPINNED=1 to force)", ctrl, (unsigned long long) rva);
        return;
    }
    logf("IClientControllerSerialized=%p vtable rva=%llx%s", ctrl, (unsigned long long) rva,
         known ? "" : " (UNPINNED — forced)");
    g_ctrl = ctrl;

    sdl_ensure();

    void** vt = *(void***) ctrl;
    typedef void (SI_THISCALL *EnableCbFn)(void* self, uint32_t appId, uint32_t zero);
    ((EnableCbFn) vt[kVtCtrl_EnableDeviceCallbacks])(ctrl, appId, 0);
    logf("EnableDeviceCallbacks(%u) done", appId);
    typedef void (SI_THISCALL *EnumFn)(void* self, uint32_t a, uint32_t b);
    ((EnumFn) vt[kVtCtrl_EnumerateControllers])(ctrl, 0, 0);
    logf("EnumerateControllers done");

    // Let the client's controller thread pick the pads up (bounded 3 s; a game without a pad still launches).
    DWORD t0 = GetTickCount();
    int n = 0;
    for (int i = 0; i < 30; ++i) {
        n = num_controllers();
        if (n > 0) break;
        Sleep(100);
    }
    logf("GetNumConnectedControllers -> %d after %lu ms", n, (unsigned long) (GetTickCount() - t0));
    g_lastCount = n;

    load_and_activate("initial");
}

// Feed every Steam callback the agent drains (CallbackMsg_t: user@0, id@4, param@8, size@16).
static void on_callback(const char* cb) {
    if (!g_ctrl) return;
    int id = *(const int*) (cb + 4);
    if (id < 2800 || id > 2899) return;
    int size = *(const int*) (cb + 16);
    if (id == kCbSteamInputDeviceConnected || id == kCbSteamInputGamepadSlotChange) {
        ++g_reactivations;
        logf("callback id=%d size=%d — re-activating after device (re)connect #%d", id, size, g_reactivations);
        load_and_activate("device (re)connect");
    } else {
        logf("callback id=%d size=%d", id, size);
    }
}

// Once per game-watch tick (1 s): report controller-count changes for the first minute after activation.
static void tick() {
    if (!g_ctrl) return;
    DWORD now = GetTickCount();
    if (now - g_activatedAt > 60000 || now - g_lastPoll < 5000) return;
    g_lastPoll = now;
    int n = num_controllers();
    if (n != g_lastCount) {
        logf("connected controllers %d -> %d", g_lastCount, n);
        g_lastCount = n;
    }
}

}  // namespace si
