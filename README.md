# winlator-contents

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
