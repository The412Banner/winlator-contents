# winlator-contents — Progress Log

**Repo:** https://github.com/The412Banner/winlator-contents
**Local path:** `/data/data/com.termux/files/home/winlator-contents`
**Rules:** No pull requests ever. `contents.json` is **isolated** — only manual edits, no automation. Log every change. Push commits as needed.

---

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
