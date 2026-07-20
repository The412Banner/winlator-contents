# winlator-contents
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/n8S4G2WZQ4)


Component catalog for Winlator-family Android clients.  this is a combination of components from my nightlies repo full of stuff ive gsthered from arihany, nick, steven, coffincolors and more over time

## What's here

A single JSON file: [`contents.json`](./contents.json) — a flat list of available components (Wine, Proton, DXVK, VKD3D, Box64, WOWBox64, FEXCore) and where to download them.

Each entry uses a four-field schema:

```json
{
  "type": "Box64",
  "verName": "Box64-0.4.3",
  "verCode": "0",
  "remoteUrl": "https://github.com/The412Banner/Nightlies/releases/download/Box64/Box64-0.4.3.wcp"
}
```

## Live URL

```
https://raw.githubusercontent.com/The412Banner/winlator-contents/main/contents.json
```

## Where the binaries live

This repo only hosts the index. The component archives (`.wcp`, `.wcp.xz`) are published as GitHub release assets on [The412Banner/Nightlies](https://github.com/The412Banner/Nightlies); every `remoteUrl` in the catalog resolves to one of those assets.

## Updates

The catalog is refreshed as new components ship. Treat it as eventually consistent with the upstream release set.


## Wrapper catalog (`wrappers.json`)

[`wrappers.json`](./wrappers.json) is the curated, downloadable **graphics wrapper** catalog (the `libvulkan_wrapper.so` ICD layer + BCn/compat layers) offered inside Bannerlator's **Wrapper Version Manager** (issue #132). It lists every wrapper from across the Winlator family (Bannerlator, WinlatorMali, WinNative, GameNative, leegao, Ludashi, Pipetto), each credited to its upstream.

Live URL:
```
https://raw.githubusercontent.com/The412Banner/winlator-contents/main/wrappers.json
```

Each entry:
```json
{
  "id": "gamenative-wrapper",
  "name": "GameNative — GameNative Wrapper",
  "description": "…",
  "author": "GameNative",
  "license": "credit GameNative",
  "url": "https://github.com/The412Banner/winlator-contents/releases/download/wrappers-v1/gamenative-20260719.tzst",
  "file_size": "745944",
  "file_checksum": "B750AFB3F536B9FE3E0986D0B6BAA6EC",
  "version": 2,
  "gpuTargets": ["all"]
}
```
- `id` — stable identifier; the app records it on install so it can recognise the wrapper later. **Never change an existing `id`.**
- `version` — a **monotonic integer**, and the **update signal**: the app compares it against the version a user installed at, and shows **"Update available"** when this is higher.
- `file_checksum` — **UPPERCASE MD5** of the `.tzst`; the download is rejected if it doesn't match.
- `gpuTargets` — `all`, or a list like `["mali","exynos"]`; entries that don't apply to the user's GPU are dimmed with a "Mali only" chip (never hard‑blocked).

### 🔧 Maintenance ritual — when a wrapper gets a new upstream build

Do these together so users are actually offered the update:

1. **Upload** the new `.tzst` as an asset on the [`wrappers-v1`](https://github.com/The412Banner/winlator-contents/releases/tag/wrappers-v1) release (use a build‑stamped name, e.g. `gamenative-20260719.tzst`, so old installs still resolve).
2. **Update the entry** in `wrappers.json`: `url`, `file_size`, `file_checksum` (UPPERCASE MD5), and — critically — **bump `version`** (`1 → 2 → …`). The version bump is what makes catalog‑installed users see **"Update available"**; changing the binary *without* bumping `version` ships a silent, un‑signalled change.
3. **If Bannerlator also *bundles* that wrapper** (i.e. it's a built‑in `wrapper-*.tzst` swapped in the app), bump the matching `catalogVersion` in the app's `app/src/main/assets/graphics_driver/bundled_wrappers.json` to the same number — otherwise the bundled slot falsely flags itself as out‑of‑date once the bundled‑slot update badge is wired.

Only bump `version` when the **binary actually changes** — it's a build identity, not an edit counter. Fork‑specific entries (e.g. `bannerlator-gamenative`, `wmali-gamenative`) reflect what *those* projects ship and move independently of the canonical upstream entry.

## Community

Join our Discord: https://discord.gg/n8S4G2WZQ4
