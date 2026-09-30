Delivery copies of the **versionCode 9** Proton / GE-Proton layers for the in-app catalog — all ten layers, 14 files. These are the same files as the build release in proton-wine — [`build-bionic-layers-20260930-v9`](https://github.com/The412Banner/proton-wine/releases/tag/build-bionic-layers-20260930-v9) — copied here server-side and checked byte-for-byte against the copies verified on device.

New in v9: **touch on Wayland**, **opt-in ntsync** (`WINENTSYNC=1`; off by default, esync unchanged), two **rsaenh crash fixes**, a dormant **Steam bridge** (`lsteamclient`, inactive unless `WINE_LSTEAMCLIENT=1`), and **Wayland + HDR10 on Proton 10.0-4 and GE-Proton 10.0-34** for the first time. The four x86_64 (box64) layers carry the ntsync and crypto fixes but not Wayland, touch or the Steam bridge, which are arm64ec-only.

They install into a new `<version>-arm64ec-9` slot beside the older ones, so nothing is overwritten and a container on an older build of the same layer is offered **Update layer → v9** with a revert snapshot.

See the build release for the full per-layer notes.
