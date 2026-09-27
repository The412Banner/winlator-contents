#!/usr/bin/env bash
# DroidDeck's base Linux runtime: only what a Steam session needs - the arm64 Steam client under
# gamescope, and Proton's games. An Arch Linux ARM rootfs from the seed list's dependency closure,
# GTK 2 for the client's UI, the media libraries Proton's GStreamer plugins link, Banners-Turnip's
# Linux driver as the default ICD, and the prebuilt proot. Everything a desktop needs is the
# separate Desktop package (desktop/build-pkg.sh); the session scripts and preloads come from the
# app at every session start (SessionFiles.stage), so none are baked in here.
#
# Ported from Bannerlator's tools/linuxfs/build-linuxfs.sh (GPL-3.0), then trimmed: no kernel,
# firmware or boot files (a proot runtime uses the phone's kernel), no docs, manuals, headers,
# non-English locales, introspection data, or the base image's server and development tools.
#   linuxfs/build-base.sh <workdir> <out.tar.zst>
# Environment:
#   TURNIP_URL   the "-Linux" Turnip zip to ship as the default driver (required)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="${1:?workdir}"
out="${2:?output tar.zst}"
: "${TURNIP_URL:?TURNIP_URL: the -Linux Turnip zip to ship as the default driver}"
mirror=http://mirror.archlinuxarm.org/aarch64
base_url=http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz

# The Steam session's closure. Bannerlator's list minus its own desktop bits (foot, pcmanfm,
# ibus): DroidDeck's Desktop package brings a desktop of its own.
seeds=(gamescope mesa vulkan-freedreno xorg-xwayland xorg-xhost xorg-xrandr vulkan-tools wayland-utils
  mesa-utils unzip dbus libpulse pulseaudio pulseaudio-alsa alsa-lib nss libnm curl ca-certificates
  fontconfig freetype2 bash coreutils grep sed gawk which findutils glib2 libglvnd libxcomposite
  libxdamage libxrandr wayland wayland-protocols libxcb libxshmfence xkeyboard-config xorg-xkbcomp
  python libxtst libxi ttf-dejavu openal libvdpau lsof zstd tar xz gzip file libevdev libinput
  gstreamer gst-plugins-base gst-plugins-base-libs gst-plugins-good gnutls libpng libjpeg-turbo)

# Packages the base image carries that no session uses; their files go, by the package database's
# own file lists, so nothing half-removed is left behind.
drop_pkgs=(linux-aarch64 linux-firmware linux-firmware-whence linux-firmware-amdgpu linux-firmware-atheros
  linux-firmware-broadcom linux-firmware-cirrus linux-firmware-intel linux-firmware-mediatek
  linux-firmware-nvidia linux-firmware-other linux-firmware-radeon linux-firmware-realtek
  linux-firmware-marvell linux-firmware-nxp linux-firmware-qcom linux-firmware-qlogic linux-firmware-liquidio
  linux-firmware-mellanox linux-api-headers binutils vim vim-runtime gettext gnupg gpgme openssh
  iptables iproute2 dhcpcd kbd e2fsprogs cryptsetup device-mapper tpm2-tss mkinitcpio kmod
  man-db man-pages texinfo groff nano ex-vi-compat gpm)

mkdir -p "$work/db" "$work/pkgs" "$work/rootfs"
cd "$work"

for repo in core extra alarm; do
  [ -s "db/$repo.db" ] || curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "db/$repo.db" "$mirror/$repo/$repo.db"
  mkdir -p "db/x_$repo"
  tar -xzf "db/$repo.db" -C "db/x_$repo"
done

# The package closure over the repository databases. Arch Linux ARM keeps %DEPENDS% in a
# separate `depends` file, and several dependencies are virtual names satisfied via %PROVIDES%.
python3 - "${seeds[@]}" > pkglist.txt <<'PY'
import os, sys, collections
pkgs, provides = {}, collections.defaultdict(list)
def strip(d):
    for sep in ("<", ">", "="):
        d = d.split(sep)[0]
    return d
for repo in ("core", "extra", "alarm"):
    root = f"db/x_{repo}"
    for entry in os.listdir(root):
        d = os.path.join(root, entry)
        fields, key = {}, None
        for fn in ("desc", "depends"):
            p = os.path.join(d, fn)
            if not os.path.exists(p): continue
            for line in open(p, encoding="utf-8", errors="replace"):
                line = line.rstrip("\n")
                if line.startswith("%") and line.endswith("%"): key = line.strip("%"); fields[key] = []
                elif key and line: fields[key].append(line)
        if not fields.get("NAME") or not fields.get("FILENAME"): continue
        n = fields["NAME"][0]
        rec = {"repo": repo, "file": fields["FILENAME"][0],
               "depends": [strip(x) for x in fields.get("DEPENDS", [])],
               "provides": [strip(x) for x in fields.get("PROVIDES", [])]}
        pkgs[n] = rec
        provides[n].append(n)
        for p in rec["provides"]: provides[p].append(n)
seen, queue, missing = set(), list(sys.argv[1:]), []
while queue:
    want = queue.pop()
    real = want if want in pkgs else (provides.get(want) or [None])[0]
    if real is None: missing.append(want); continue
    if real in seen: continue
    seen.add(real)
    queue.extend(pkgs[real]["depends"])
if missing: sys.exit("unresolved: " + " ".join(missing))
for n in sorted(seen): print(pkgs[n]["repo"] + "/" + pkgs[n]["file"])
PY
echo "$(wc -l < pkglist.txt) packages in the closure"
while read -r entry; do
  file=${entry#*/}
  if ! tar -tf "pkgs/$file" >/dev/null 2>&1; then
    rm -f "pkgs/$file"
    curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "pkgs/$file" "$mirror/$entry"
    tar -tf "pkgs/$file" >/dev/null
  fi
done < pkglist.txt

[ -s base.tar.gz ] || curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o base.tar.gz "$base_url"
rm -rf rootfs && mkdir rootfs
tar -xzf base.tar.gz -C rootfs --no-same-owner --no-same-permissions --exclude=dev 2>/dev/null || true
echo "base image: $(du -sm rootfs | cut -f1) MB"
while read -r entry; do
  file=${entry#*/}
  tar -xf "pkgs/$file" -C rootfs --no-same-owner --no-same-permissions \
    --exclude=.PKGINFO --exclude=.MTREE --exclude=.INSTALL --exclude=.BUILDINFO --exclude=.CHANGELOG
done < pkglist.txt
# Everything is read and written as one unprivileged user, here and on the device: a package's
# setuid helper (dbus-daemon-launch-helper, mode 4750) must not stay unreadable to that user.
chmod -R u+rwX rootfs
echo "with the closure: $(du -sm rootfs | cut -f1) MB"

# --- trim ------------------------------------------------------------------------------------
# Whole packages from the base image, by the package database's file lists.
for p in "${drop_pkgs[@]}"; do
  for d in rootfs/var/lib/pacman/local/"$p"-[0-9]*; do
    [ -f "$d/files" ] || continue
    # `files` lists paths relative to /, directories with a trailing slash; files first, then
    # any directory the package owned that is now empty.
    # grep finds nothing in a list of only files or only directories; that is not a failure.
    { grep -vE '^%|^\s*$' "$d/files" || true; } | { grep -v '/$' || true; } | sed 's#^#rootfs/#' | xargs -r -d '\n' rm -f --
    { grep -vE '^%|^\s*$' "$d/files" || true; } | { grep '/$' || true; } | sort -r | sed 's#^#rootfs/#' | xargs -r -d '\n' rmdir --ignore-fail-on-non-empty -- 2>/dev/null || true
    rm -rf "$d"
    echo "  dropped $(basename "$d")"
  done
done
rm -rf rootfs/boot rootfs/usr/lib/modules rootfs/usr/lib/firmware
# Files no session reads.
rm -rf rootfs/usr/share/{doc,man,info,gtk-doc,gir-1.0,vala,i18n,zoneinfo-leaps,help}
rm -rf rootfs/usr/include rootfs/usr/lib/pkgconfig rootfs/usr/share/pkgconfig rootfs/usr/lib/cmake
find rootfs/usr/lib -name '*.a' -type f -delete
find rootfs/usr/share/locale -mindepth 1 -maxdepth 1 -type d ! -name 'en*' -exec rm -rf {} + 2>/dev/null || true
find rootfs/usr/share/icons -mindepth 1 -maxdepth 1 -type d ! -name hicolor -exec rm -rf {} + 2>/dev/null || true
rm -rf rootfs/usr/lib/python3.*/{test,tests,idlelib,tkinter,ensurepip,turtledemo,lib2to3}
find rootfs/usr/lib/python3.* -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "trimmed: $(du -sm rootfs | cut -f1) MB"

# --- the client's GTK 2 and Proton's media libraries (as in Bannerlator's builder) --------------
gtk2_deb=libgtk2.0-0t64_2.24.33-7_arm64.deb
gtk2_sha=28b2f1622197443f07f25a93e03db1a964184946ac12f501b8221c895026d0ca
[ -s "pkgs/$gtk2_deb" ] || curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "pkgs/$gtk2_deb" "http://deb.debian.org/debian/pool/main/g/gtk+2.0/$gtk2_deb"
echo "$gtk2_sha  pkgs/$gtk2_deb" | sha256sum -c --quiet
rm -rf gtk2 && mkdir gtk2 && (cd gtk2 && ar x "../pkgs/$gtk2_deb" && tar -xf data.tar.*)
for n in gtk gdk; do
  install -m 755 "gtk2/usr/lib/aarch64-linux-gnu/lib$n-x11-2.0.so.0.2400.33" rootfs/usr/lib/
  ln -sfn "lib$n-x11-2.0.so.0.2400.33" "rootfs/usr/lib/lib$n-x11-2.0.so.0"
done
gst_debs="
libnettle8_3.8.1-2_arm64.deb c945ff210df69cf7b95e935b8fa936e81c1c1f475355e3d5db83510b174f0cd6 https://deb.debian.org/debian/pool/main/n/nettle/libnettle8_3.8.1-2_arm64.deb
libtheora0_1.1.1+dfsg.1-16.1build3_arm64.deb 78ebaa1c851465dac9e13532623a4e41d28ed55f3df0353daf7c29d96a2e2b87 http://ports.ubuntu.com/ubuntu-ports/pool/main/libt/libtheora/libtheora0_1.1.1+dfsg.1-16.1build3_arm64.deb
libvpx9_1.14.0-1ubuntu2_arm64.deb 809bf0d9435520793838a99072ca365ab23956def3583c3b8b4e253135d8e9f4 http://ports.ubuntu.com/ubuntu-ports/pool/main/libv/libvpx/libvpx9_1.14.0-1ubuntu2_arm64.deb
"
rm -rf gstlibs && mkdir gstlibs
while read -r deb sha url; do
  [ -n "$deb" ] || continue
  [ -s "pkgs/$deb" ] || curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "pkgs/$deb" "$url"
  echo "$sha  pkgs/$deb" | sha256sum -c --quiet
  (cd gstlibs && ar x "../pkgs/$deb" && tar -xf data.tar.* && rm -f data.tar.* control.tar.* debian-binary)
done <<< "$gst_debs"
find gstlibs/usr/lib -maxdepth 2 -name '*.so.*' -type f -exec cp -a {} rootfs/usr/lib/ \;
for so in rootfs/usr/lib/libnettle.so.8.* rootfs/usr/lib/libtheoradec.so.1.* rootfs/usr/lib/libtheoraenc.so.1.* \
          rootfs/usr/lib/libtheora.so.0.* rootfs/usr/lib/libvpx.so.9.*; do
  [ -f "$so" ] || continue
  base=$(basename "$so")
  ln -sfn "$base" "rootfs/usr/lib/$(echo "$base" | sed -E 's/(\.so\.[0-9]+).*/\1/')"
done
ls -l rootfs/usr/lib/libnettle.so.8 rootfs/usr/lib/libtheoradec.so.1 rootfs/usr/lib/libvpx.so.9

# --- the default Vulkan driver: Banners-Turnip's Linux build ------------------------------------
curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o turnip.zip "$TURNIP_URL"
rm -rf turnip && mkdir turnip && (cd turnip && unzip -q ../turnip.zip)
install -m 755 turnip/libvulkan_freedreno.so rootfs/usr/lib/libvulkan_freedreno.so
mkdir -p rootfs/usr/share/vulkan/icd.d
printf '{\n    "ICD": {\n        "api_version": "1.4.0",\n        "library_path": "/usr/lib/libvulkan_freedreno.so"\n    },\n    "file_format_version": "1.0.0"\n}\n' \
  > rootfs/usr/share/vulkan/icd.d/freedreno_icd.json
rm -f rootfs/usr/share/vulkan/icd.d/nvidia_icd.json
cp turnip/meta.json rootfs/usr/share/vulkan/icd.d/freedreno_icd.meta.json 2>/dev/null || true

# --- the runtime's own proot, and what Xwayland and Steam expect of a system -------------------
mkdir -p rootfs/opt/android-host
cp -a "$here"/prebuilt/proot/proot "$here"/prebuilt/proot/loader "$here"/prebuilt/proot/libtalloc.so.2 \
      "$here"/prebuilt/proot/README.md rootfs/opt/android-host/
chmod 755 rootfs/opt/android-host/proot rootfs/opt/android-host/loader
mkdir -p rootfs/dev rootfs/proc rootfs/sys rootfs/tmp rootfs/root rootfs/run/user rootfs/usr/local/lib rootfs/usr/local/bin
chmod 1777 rootfs/tmp
printf '/usr/local/lib\n/usr/lib\n/usr/lib32\n' > rootfs/etc/ld.so.conf
rm -f rootfs/etc/ld.so.cache rootfs/etc/machine-id rootfs/etc/resolv.conf
head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n' > rootfs/etc/machine-id
printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > rootfs/etc/resolv.conf
printf 'root:x:0:0:root:/root:/bin/bash\n' > rootfs/etc/passwd
printf 'root:x:0:\n' > rootfs/etc/group
# What pacman's hooks would have built: the mime database, pixbuf loaders, the icon cache and the
# linker cache, made inside the rootfs under qemu.
proot -q "$(command -v qemu-aarch64-static)" -r rootfs -w / -b /dev -b /proc /bin/bash -c '
  export PATH=/usr/bin:/bin
  [ -d /usr/share/mime ] && update-mime-database /usr/share/mime >/dev/null 2>&1 || true
  q=$(ls -d /usr/lib/gdk-pixbuf-2.0/2.10.0/loaders 2>/dev/null | head -1)
  [ -n "$q" ] && gdk-pixbuf-query-loaders --update-cache >/dev/null 2>&1 || true
  [ -d /usr/share/icons/hicolor ] && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
  ldconfig -r / >/dev/null 2>&1 || true
' || echo "post-install hooks under qemu: best effort"
echo "final: $(du -sm rootfs | cut -f1) MB"
for f in usr/bin/gamescope usr/bin/Xwayland usr/lib/libvulkan_freedreno.so usr/lib/libgtk-x11-2.0.so.0 \
         usr/bin/pulseaudio usr/bin/python3 opt/android-host/proot usr/lib/libnettle.so.8; do
  [ -e "rootfs/$f" ] || { echo "MISSING from rootfs: $f" >&2; exit 1; }
done
mkdir -p "$(dirname "$out")"
tar -C rootfs --zstd -cf "$out" .
ls -l "$out"
sha256sum "$out"
