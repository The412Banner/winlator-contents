# winlator-contents

Component catalog index for BannerHub / Winlator-family Android clients.

## What this repo is

A single JSON file: [`contents.json`](./contents.json).

It's a flat list of component entries (Box64, FEXCore, DXVK, VKD3D, WOWBox64, GpuDriver, …) using the same 4-field schema as [Nick's `content.json`](https://raw.githubusercontent.com/Xnick417x/Winlator-Bionic-Nightly-wcp/refs/heads/main/content.json):

```json
{
  "type": "Box64",
  "verName": "Box64-0.4.3",
  "verCode": "0",
  "remoteUrl": "https://github.com/The412Banner/Nightlies/releases/download/Box64/Box64-0.4.3.wcp"
}
```

## What it is not

The component **binaries** (`.wcp` / `.tzst` files) do **not** live here. They live on the GitHub releases of [`The412Banner/Nightlies`](https://github.com/The412Banner/Nightlies) (the build-tracking repo). Every `remoteUrl` in `contents.json` points back at a release asset there.

Splitting them keeps the metadata index lightweight and easy to mirror, while the binary distribution stays in Nightlies where the auto-watcher pipeline already manages it.

## Live URL

```
https://raw.githubusercontent.com/The412Banner/winlator-contents/main/contents.json
```

## How it's updated

Right now, **manually mirrored** from `The412Banner/Nightlies/nightlies_components.json` whenever that file moves forward. Automation is intentionally deferred — we'll either push from the Nightlies watcher or pull on a schedule from this repo, but the choice hasn't been made yet.

If you depend on this URL, treat the file as eventually-consistent with the upstream Nightlies release set.
