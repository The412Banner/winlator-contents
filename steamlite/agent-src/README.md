# SteamLite agent (steam.exe) — corresponding source

GPL-3.0 clean-room Steam agent shipped inside `steamlite.tzst` (release `steamlite-v1`,
package version 10, agent "p8", 2026-11-23). Derived from WinNative's
`wn-steam-launcher` (GPL-3.0) — see NOTICE.md for attribution and the change history.

Build (MinGW-w64, x86_64 PE; runs in-Wine under Proton arm64ec + FEX):

    x86_64-w64-mingw32-g++-posix -std=c++17 -O2 -s -static -static-libgcc -static-libstdc++ \
      -Wl,--subsystem,windows -I. -o steam.exe main.cpp clean_shutdown.cpp -ladvapi32 -lws2_32

Shipped binary: md5 cc80fcb92686136d7bcd4de0f80d87da (1,167,360 bytes), built by Bannerlator CI
run 45327465984 from tools/steamlite-agent at 48b4bafb (same tree as this folder).
Only steam.exe is ours; the Valve client files in the package are not GPL (VALVE_COMPONENTS.txt).

Agent p7 (2026-10-05, package v8): `steam_input.h` — Steam Input activation for the launched app
(`WN_STEAM_INPUT=1` / `WN_STEAM_INPUT_VDF`), header-only, inert without the env. Same build line
(`steam_input.h` is included by `main.cpp`).

Agent p8 (2026-11-23, package v10): passes the shortcut's launch arguments to the game. `main.cpp`
reads `WN_STEAM_USER_ARGS` (set by Bannerlator) and hands it to `LaunchApp` as the user arguments and
after the exe on the CreateProcess start; only the length is logged; inert without the env.
Ported from Winlator Ludashi 54fa905f by StevenMXZ (GPL-3.0).
