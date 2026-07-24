# winlator-contents — Progress Log

**Repo:** https://github.com/The412Banner/winlator-contents
**Local path:** `/data/data/com.termux/files/home/winlator-contents`
**Rules:** No pull requests ever. `contents.json` is **isolated** — only manual edits, no automation. Log every change. Push commits as needed.

---

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
