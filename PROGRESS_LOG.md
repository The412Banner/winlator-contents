# winlator-contents — Progress Log

**Repo:** https://github.com/The412Banner/winlator-contents
**Local path:** `/data/data/com.termux/files/home/winlator-contents`
**Rules:** No pull requests ever. `contents.json` is **isolated** — only manual edits, no automation. Log every change. Push commits as needed.

---

## Session — 2026-08-29

### [dxvk] — Add DXVK 3.1 stable entries (vanilla + gplasync, std + arm64ec)

#### What changed
- `contents.json` — added 4 new `DXVK` entries, one per catalog family, each inserted directly after
  that family's `3.0.2` entry. `verCode` "0" like every other DXVK entry:
    - `dxvk-3.1`                     → `Dxvk/dxvk-3.1.wcp` (vanilla std)
    - `dxvk-arm64ec-3.1`            → `Dxvk-arm64ec/dxvk-arm64ec-3.1.wcp` (vanilla arm64ec)
    - `dxvk-gplasync-3.1-1`         → `Dxvk-gplasync/dxvk-gplasync-3.1-1.wcp` (gplasync std)
    - `dxvk-gplasync-arm64ec-3.1-1` → `Dxvk-gplasync-arm64ec/dxvk-gplasync-arm64ec-3.1-1.wcp` (gplasync arm64ec)
- DXVK entries 54 → 58; total 167 → 171.
- **binsem-gplasync 3.1 NOT added** — the Bannerlator catalog has never carried binsem entries (only vanilla + gplasync).
- ⚠️ **Binaries not yet on the dedicated Nightlies stable releases** — these 4 URLs 404 until the matching
  `.wcp` files are uploaded to the `Dxvk` / `Dxvk-arm64ec` / `Dxvk-gplasync` / `Dxvk-gplasync-arm64ec` release tags
  with the EXACT filenames above. (Source files staged in device Downloads as `DXVK-v3.1*.wcp`.)

---

## Session — 2026-08-17

### [proton] — Consolidate all arm64ec bionic Proton entries onto `build-bionic-layers-20260817-arihany` and add GE-Proton 10.0-34

#### What changed
- `contents.json` — all six existing arm64ec bionic Proton entries repointed from their per-tag DirectAudio releases
  (`build-p11-20260815`, `build-p10-20260815`, `build-ge11.3-20260816-da131`, `build-ge11.5-20260811`) to the new
  consolidated release `build-bionic-layers-20260817-arihany`, and `verCode`s bumped to match the release profile stamps
  so clients re-pull:
    - `proton-11.0-1-arm64ec-unixlibs-sdk{28,35}`  vc 3 → **4**
    - `proton-10.0-4-arm64ec-unixlibs-sdk{28,35}`  vc 4 → **5**
    - `ge-proton-11.0-3-arm64ec-sdk{28,35}`        vc 7 → **8**  (also drops the `-DA.wcp` asset-name suffix — the consolidated release uses the plain name)
    - `ge-proton-11.0-5-arm64ec-sdk{28,35}`        vc 1 → **6**
- Added two brand-new entries for the new **GE-Proton 10.0-34** Wine-10 layer (Valve Proton 10.0-4 base + GE-Proton10-34
  game-fix tier + our extras — battlenet / maplestory×2 / WM_ACTIVATEAPP), vc 1:
    - `ge-proton-10.0-34-arm64ec-sdk28`  → `GE-proton-10.0-34-arm64ec-sdk28.wcp`
    - `ge-proton-10.0-34-arm64ec-sdk35`  → `GE-proton-10.0-34-arm64ec-sdk35.wcp`
- Context: today's `build-bionic-layers-20260817-arihany` is one consolidated release carrying all five bionic
  arm64ec layers with the three arihany Android compat fixes (SD-card `noexec`/`force_anon` boot fix, File Explorer
  drive-root → drive-root copy, `C.UTF-8` locale default) + DirectAudio v1.3.1 (Wine-11 layers vendored, Wine-10 layers
  use the Wine-10 ABI port `directaudio@4241123a`). Each layer's vc = the release's profile stamp so this installs as a
  distinct new layer alongside anything users already had installed. The three legacy Nightlies rows
  (`proton-9.0-arm64ec`, `proton-9.0-x86_64`, `proton-10.0-arm64ec`) are intentionally untouched.

---

## Session — 2026-08-15

### [proton] — Repoint the two Proton 10.0-4 "unixlibs" options to the DirectAudio `build-p10-20260815` release

#### What changed
- `contents.json` — both `proton-10.0-4-arm64ec-unixlibs-sdk28` and `-sdk35` entries repointed from the old
  `build-arm64ec-refresh-20260722` assets to the DirectAudio-v1.3.1 assets on the new release
  (`proton-10.0-4-arm64ec-sdk{28,35}.wcp` under `build-p10-20260815`), and `verCode` bumped `3 → 4` so clients re-pull.
- Context: the new release is a refresh of `build-p10-20260713` with DirectAudio v1.3.1 (Wine 10 ABI port) folded in;
  built from `proton_10.0` @ `5bffd6e7`, SDK28 `31898126463` + SDK35 `31898126471` CI green. Device-verified on
  DiRT Showdown (DirectAudio live via AAudio). vc bump 3→4 matches the release profile stamp so it installs as a new layer.

---

## Session — 2026-08-15

### [proton] — Repoint the two Proton 11.0-1 "unixlibs" options to the rebuilt `build-p11-20260815` release

#### What changed
- `contents.json` — both `proton-11.0-1-arm64ec-unixlibs-sdk28` and `-sdk35` entries repointed from the old
  `build-arm64ec-refresh-20260722` assets to the rebuilt DirectAudio-v1.3.1 assets on the new release
  (`proton-11.0-1-arm64ec-sdk{28,35}.wcp` under `build-p11-20260815`), and `verCode` bumped `2 → 3` so clients re-pull.
- Context: the old refresh build was a skeleton (missing the DirectAudio PE side); rebuilt from
  `proton_11.0` @ `3e9d0c8`, 4/4 CI green. New assets carry the corrected layer (no DXVK bundled, verified).

---

## Session — 2026-08-06

### [d7vk] — Add D7VK (DirectDraw/D3D7) component + `d7vk-v1` release (2026-08-06)

#### What changed
- Created release **`d7vk-v1`** on this repo and uploaded `d7vk-v2.1-bc3b29b9e-nightly.wcp`
  (2,472,124 B — `syswow64/ddraw.dll` + `profile.json` type `D7VK`). Built by the new
  Nightlies `build-d7vk` job from `WinterSnowfall/d7vk` `devel` (2.x product line, commit
  `bc3b29b9e`), 32-bit only, GCC `std::sqrtf`→`std::sqrt` shim applied.
- Added a `contents.json` entry (last element, #158):
  `{type:"D7VK", verName:"v2.1-bc3b29b9e-nightly", verCode:"0",
   remoteUrl:.../releases/download/d7vk-v1/d7vk-v2.1-bc3b29b9e-nightly.wcp}`.
- **verName is the .wcp's internal `profile.json` versionName (`v2.1-bc3b29b9e-nightly`),
  NOT the filename stem** — required so `ContentsManager.java:160` reconciles the catalog
  entry against the installed profile (verName equality). Device-proven: installed+applied
  on device via the app's "D7VK Version" cloud dropdown (`CONTENT_TYPE_D7VK`).
- Handled a concurrent FEXCore-2608 push mid-edit: reset to latest origin and re-appended
  cleanly (no clobber).

#### Files touched
- `contents.json`
- `PROGRESS_LOG.md`

## Session — 2026-07-25

### [wrapper] — Bump `gamenative-wrapper` catalog entry to upstream GameNative #1771 (2026-07-25)

#### What changed
- Uploaded `gamenative-20260725.tzst` (748,724 B, md5 `CE7E20E37431FD808C361B8C33ED53E9`) to this repo's `wrappers-v1` release.
- Repointed the `gamenative-wrapper` entry in `wrappers.json` (the "canonical latest upstream" GameNative wrapper): `url` → the new asset, `file_size` `747484`→`748724`, `file_checksum` `D6F3A6371FD5E8ECEC1053EBFBE5638B`→`CE7E20E37431FD808C361B8C33ED53E9`, `version` `3`→`4`, description updated to `20260725 / #1771`. Previous state was `20260723 / #1762`.
- **Source:** `utkarshdalal/GameNative` `master`, file `app/src/legacy/assets/graphics_driver/wrapper-gamenative.tzst`, last updated by **PR #1771** (commit `790ce5d264a0d13e3f61cefdb219a7c82b4504d6`, 2026-07-25, "Updated wrapper-gamenative with leegao's latest changes"). Upstream `.tzst` was byte-verified against the pinned commit.
- **Repacked clean:** upstream archive was Mac-packed (carried `LIBARCHIVE.xattr.com.apple.provenance` pax headers). Re-tarred from the extracted tree (`--sort=name --owner=0 --group=0 --numeric-owner`, zstd -19) so the shipped archive has no Apple xattrs / `._` junk. **Payload byte-identical to upstream** — the only file that changes vs our prior #1762 build is `libvulkan_wrapper.so` (md5 `b3e8d9797ce8146c63bcda964d6df01a`, compiled `Jul 24 2026`); adrenotools/hook libs/ICD json are unchanged across #1762→#1771.
- **Scope:** ONLY `gamenative-wrapper` updated. `bannerlator-gamenative` / `wmali-gamenative` left as-is on purpose — those entries mirror the forks' *actual* shipped builds (`gamenative.tzst`, Jul 5), so rebranding them to upstream would falsify their "byte-identical to WinlatorMali's build" descriptions.
- Old assets (`gamenative-20260723.tzst` etc.) left attached to the release for rollback.

#### Files touched
- `wrappers.json`
- `PROGRESS_LOG.md`

## Session — 2026-07-24

### [chore] — Replace the `fexcore-v1` nightly-unix build with FEX-2607+312 (2026-07-24)

#### What changed
- Swapped the single asset on this repo's `fexcore-v1` release: deleted `FEXCore-2607-nightly-unix.wcp` (982,604 B, sha256 `6d3974dc…`) and uploaded `FEX-2607+312-Nightly-464ec9d0b-unix.wcp` (990,348 B, sha256 `de3a3ac027201f80a9c35c1718593e7dd1d578a0be68d8aa176c5b5b4d0722d1`, built 2026-07-24).
- Repointed the matching `contents.json` entry (still 151 entries, 22 FEXCore): `verName` `FEXCore-2607-nightly-unix` → `FEX-2607+312-Nightly-464ec9d0b-unix` (matches the `versionName` inside the new `profile.json`, so the installed component and the catalog row dedupe as one), `remoteUrl` → the new asset. `verCode` stays `0`.
- URL uses `%2B` for the `+` in the filename. Both `%2B` and literal `+` were curl-verified `200` with the correct sha256; the encoded form is the canonical one in the catalog.
- Same 4-file unixlib layout as the outgoing build — `system32/lib{arm64ec,wow64}fex.dll` + `aarch64-unix/lib{arm64ec,wow64}fex.so` — so it is a drop-in for the FEXCore unixlib slot.
- Old asset kept as a local backup only (not on the release anymore).

#### Files touched
- `contents.json`
- `PROGRESS_LOG.md`

## Session — 2026-07-12

### [chore] — Point Proton 11.0-1 entries at rebuilt `build-p11-20260712` (2026-07-12)

#### What changed
- Repointed all four `proton-11.0-1-{arm64ec,x86_64}-sdk{28,35}` `remoteUrl`s from the older sources to the new `The412Banner/proton-wine` release `build-p11-20260712`. Filenames + `verName`s unchanged (drop-in), so clients see the same catalog identity.
  - arm64ec pair: `build-p11-20260709` → `build-p11-20260712`.
  - x86_64 pair: moved off this repo's own `proton-11.0-1-x86_64` self-release → `proton-wine/build-p11-20260712`, consolidating all four assets under one tag.
- New builds are debug-stripped + zstd-compressed: arm64ec ~94.5 MB, x86_64 ~61.5 MB (~⅓ prior download, ~730 MB installed vs ~2 GB). Runtime unchanged (still Proton 11.0-1). All four asset URLs HEAD-verified `302`.

#### Files touched
- `contents.json`

## Session — 2026-07-03

### [feat] — Add FEXCore 2607 stables (non-PPA + PPA) to contents.json (2026-07-03)

#### What changed
- Added two `FEXCore` entries to `contents.json` (142 → 144), inserted contiguously after the last FEXCore entry:
  - `FEXCore-2607` → `Nightlies/releases/download/FexCore/FEXCore-2607.wcp`
  - `FEXCore-2607-PPA` → `Nightlies/releases/download/FexCore/FEXCore-2607-PPA.wcp`
- Both are the FEX-2607 stable builds (cut from the exact `FEX-2607` tag, commit `1cc4b93e`); `.wcp` assets already live on the Nightlies `FexCore` release (URLs verified 200). `verCode` `0`, naming matches the existing `FEXCore-2605` convention.

## Session — 2026-05-08

### [feat] — Add `.wcp.xz` Wine + Proton entries to catalog (2026-05-08)
**Commit:** `4624fd1`

#### What changed
- Added `wine-11.3-arm64ec` and `proton-10-arm64ec` to `contents.json` (158 → 160). Both reference `.wcp.xz` assets in the `Proton/wine` release on `Nightlies`, which the upstream watcher's `.wcp`-only filter currently skips. `verName` strips the full `.wcp.xz` extension (consistent with the convention for `.wcp` entries).
- Mirror entries also added to `Nightlies/nightlies_components.json` (re-applied at `d004d9d` after a watcher wipe).

#### Files touched
- `contents.json`

---

### [docs] — Rewrite README (2026-05-08)
**Commit:** `65e8d88`

#### What changed
- Tightened README to four short sections: tagline, what's here (with schema example), live raw URL, where binaries live, updates. No upstream-attribution references, no internal sync mechanics, no deferred-automation talk.

#### Files touched
- `README.md`

---

### [chore] — Strip `nightly-latest` entries (2026-05-08)
**Commit:** `5b0bfc9`

#### What changed
- Removed all 22 `nightly-latest` rolling-tag entries (160 → 138): 8 Box64 · 4 DXVK · 4 VKD3D · 4 WOWBox64 · 2 FEXCore.
- Reason: duplicated archived versions and contained type/filename mismatches (WOWBox64 builds under `type: Box64`, etc.).
- Mirrored the same removal to `Nightlies/nightlies_components.json` at `b2d392e`. Note: the Nightlies-side delete will be re-applied by the watcher on its next run unless `nightlies-components-json.yml` lines 98–115 are removed.

#### Files touched
- `contents.json`

---

## Repo state (2026-05-08)

- Entries: **138** — DXVK 45, Box64 23, FEXCore 18, Wine 20, VKD3D 14, WOWBox64 12, Proton 6.
- Workflows on this repo: **none**. No GitHub Actions, no automation, no cross-repo writes. `contents.json` only changes via direct manual edits + push.
- Source-of-truth model: `Nightlies/nightlies_components.json` is upstream; mirrored manually here, with selective edits (e.g. the `nightly-latest` strip above) preserved on the mirror side.
- Future plan (deferred): an auto-update workflow living **inside this repo** (not cross-pushed from Nightlies) that pulls + filters from the upstream JSON. Not built yet.
