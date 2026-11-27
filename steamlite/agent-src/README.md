# SteamLite agent (steam.exe) — corresponding source

GPL-3.0 clean-room Steam agent shipped inside `steamlite.tzst` (release `steamlite-v1`,
package version 12, agent "p10", 2026-11-27). Derived from WinNative's
`wn-steam-launcher` (GPL-3.0) — see NOTICE.md for attribution and the change history.

Build (MinGW-w64, x86_64 PE; runs in-Wine under Proton arm64ec + FEX):

    x86_64-w64-mingw32-g++-posix -std=c++17 -O2 -s -static -static-libgcc -static-libstdc++ \
      -Wl,--subsystem,windows -I. -o steam.exe main.cpp clean_shutdown.cpp -ladvapi32 -lws2_32

Shipped binary: md5 051d7d827265f017e359bd3027ee0cc3 (1,169,408 bytes), built by Bannerlator CI
run 46015043546 from tools/steamlite-agent at 123d9a94 (same tree as this folder; = Bannerlator main f01f0fad).
Only steam.exe is ours; the Valve client files in the package are not GPL (VALVE_COMPONENTS.txt).

Agent p7 (2026-10-05, package v8): `steam_input.h` — Steam Input activation for the launched app
(`WN_STEAM_INPUT=1` / `WN_STEAM_INPUT_VDF`), header-only, inert without the env. Same build line
(`steam_input.h` is included by `main.cpp`).

Agent p8 (2026-11-23, package v10): passes the shortcut's launch arguments to the game. `main.cpp`
reads `WN_STEAM_USER_ARGS` (set by Bannerlator) and hands it to `LaunchApp` as the user arguments and
after the exe on the CreateProcess start; only the length is logged; inert without the env.
Ported from Winlator Ludashi 54fa905f by StevenMXZ (GPL-3.0).

Agent p9 (2026-11-27, package v11): steam:// URL launch. In a Bannerlator container desktop, EA Desktop's
Play button on a Steam-owned game opens `steam://run/<appid>`; `main.cpp` takes the app from the URL
(`run/`, `rungameid/`, `launch/`), the game and per-game settings from Bannerlator's spec `C:\<appid>.spec`
(KEY=VALUE lines after the app id), restarts itself with `PROTON_DISABLE_LSTEAMCLIENT=1`, shows a message box
when the session has no Steam sign-in or no spec, holds the Steam session 60 s after the game (900 s for
shortcut launches, unchanged) and ends its process after the clean logoff. Inert for shortcut launches.

Agent p10 (2026-11-27, package v12): before an EA-chain launch (`WN_STEAM_LAUNCH_CHAIN` set) `main.cpp` deletes
EA's cached game licences `C:\ProgramData\Electronic Arts\EA Services\License\*.dlf` (not `*_cached`) older than
`WN_EA_LICENCE_MAX_AGE_S` (default 600 s; negative = off), so EA fetches a fresh licence through its short token
(OOA 4.2 cannot renew a stale licence with the Steam-linked EA app's long JWS token).
