Delivery copies of the **versionCode 8** Proton / GE-Proton layers for the in-app catalog. These are the same files as the build release in proton-wine — [`build-bionic-layers-20260917-wayland-v8`](https://github.com/The412Banner/proton-wine/releases/tag/build-bionic-layers-20260917-wayland-v8) — copied here server-side and checked byte-for-byte against the copies verified on device.

Every arm64ec layer carries **Wayland** (`winewayland.drv` plus eight bundled Wayland Turnip drivers) and **HDR10** reporting. The four x86_64 (box64) layers carry everything else at versionCode 8 but not Wayland, which is arm64ec-only.

They install into a new `<version>-arm64ec-8` slot beside v7's `-7`, so nothing is overwritten and a container on a `-7` layer is offered this as an **Update layer → v8** with a revert snapshot.

**Proton 10.0-4 and GE-Proton 10.0-34 are not here** — they stay at versionCode 7 and keep their v7 delivery copies.

See the build release for the full per-layer notes.
