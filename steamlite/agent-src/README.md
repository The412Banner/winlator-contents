# SteamLite agent (steam.exe) — corresponding source

GPL-3.0 clean-room Steam agent shipped inside `steamlite.tzst` (release `steamlite-v1`,
package version 8, agent "p7", 2026-10-05). Derived from WinNative's
`wn-steam-launcher` (GPL-3.0) — see NOTICE.md for attribution and the change history.

Build (MinGW-w64, x86_64 PE; runs in-Wine under Proton arm64ec + FEX):

    x86_64-w64-mingw32-g++-posix -std=c++17 -O2 -s -static -static-libgcc -static-libstdc++ \
      -Wl,--subsystem,windows -I. -o steam.exe main.cpp clean_shutdown.cpp -ladvapi32 -lws2_32

Shipped binary: md5 ffb1f9429f5a51df45689175c1fa2a9c (1,198,080 bytes).
Only steam.exe is ours; the Valve client files in the package are not GPL (VALVE_COMPONENTS.txt).

Agent p7 (2026-10-05, package v8): `steam_input.h` — Steam Input activation for the launched app
(`WN_STEAM_INPUT=1` / `WN_STEAM_INPUT_VDF`), header-only, inert without the env. Same build line
(`steam_input.h` is included by `main.cpp`).
