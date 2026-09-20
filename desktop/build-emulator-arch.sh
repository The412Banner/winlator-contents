#!/bin/bash
# Builds PCSX2 or Cemu for aarch64 inside an Arch Linux ARM container and packages it as an
# AppImage. Arch because both need newer libraries than any Ubuntu runner image has (PCSX2:
# Qt 6.10, Cemu: wxWidgets 3.3) and because the app's rootfs is Arch Linux ARM itself, so
# what is built here links against the same glibc it will run on.
#   docker run --rm -v "$PWD:/work" -w /work menci/archlinuxarm:base-devel bash desktop/build-emulator-arch.sh pcsx2
set -euo pipefail
T=${1:?target: pcsx2 | cemu}
J=$(nproc)

# pacman 7's download sandbox (Landlock + the alpm user) cannot be set up inside a container.
sed -i 's/^\[options\]/[options]\nDisableSandbox/' /etc/pacman.conf
pacman-key --init >/dev/null 2>&1 || true
pacman-key --populate archlinuxarm >/dev/null 2>&1 || true
pacman -Syu --noconfirm --needed >/dev/null
COMMON="git cmake ninja clang llvm lld extra-cmake-modules pkgconf python file patchelf desktop-file-utils squashfs-tools
  qt6-base qt6-svg qt6-tools qt6-wayland vulkan-headers vulkan-icd-loader libx11 libxrandr libxext libxi libxcb
  wayland wayland-protocols libdecor alsa-lib libpulse libevdev curl zlib zstd lz4 bzip2 xz libpng
  libjpeg-turbo libwebp freetype2 fontconfig dbus hidapi libusb bluez-libs sdl3 shaderc ffmpeg libpcap libaio
  libzip fmt glm glslang pugixml rapidjson boost zarchive gtk3 libsecret libgcrypt freeglut wxwidgets-common
  kddockwidgets directx-headers libbacktrace"
# shellcheck disable=SC2086
pacman -S --noconfirm --needed $COMMON 2>&1 | grep -vE "is up to date|^\s*$" | tail -20
git config --global --add safe.directory '*'
mkdir -p /opt/deps
export CMAKE_PREFIX_PATH=/opt/deps:/usr

# Small libraries the repos lack, built the way PCSX2's own dependency script builds them.
dep() { # name, git url, ref, cmake flags...
  local name=$1 url=$2 ref=$3; shift 3
  [ -d "/opt/src/$name" ] || git clone -q --depth 1 -b "$ref" --recurse-submodules --shallow-submodules "$url" "/opt/src/$name"
  cmake -S "/opt/src/$name" -B "/opt/src/$name/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/opt/deps -DBUILD_SHARED_LIBS=ON "$@" >/dev/null
  cmake --build "/opt/src/$name/build" -j"$J" >/dev/null
  cmake --install "/opt/src/$name/build" >/dev/null
  echo "== dep $name ($ref) built"
}

case "$T" in
  pcsx2)
    dep plutovg   https://github.com/sammycage/plutovg.git  v1.3.3 -DPLUTOVG_BUILD_EXAMPLES=OFF
    dep plutosvg  https://github.com/sammycage/plutosvg.git v0.0.8 -DPLUTOSVG_ENABLE_FREETYPE=ON -DPLUTOSVG_BUILD_EXAMPLES=OFF
    dep rapidyaml https://github.com/biojppm/rapidyaml.git  v0.12.1 -DRYML_BUILD_TOOLS=OFF -DRYML_BUILD_TESTS=OFF
    git clone -q --depth 1 https://github.com/PCSX2/pcsx2.git src
    git -C src submodule update -q --init --recursive --depth 1
    cmake -S src -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_EXE_LINKER_FLAGS_INIT="-fuse-ld=lld" -DCMAKE_MODULE_LINKER_FLAGS_INIT="-fuse-ld=lld" \
      -DENABLE_SETCAP=OFF -DDISABLE_ADVANCE_SIMD=TRUE -DUSE_LINKED_FFMPEG=ON -DPACKAGE_MODE=OFF \
      -DCMAKE_INSTALL_PREFIX=/usr
    cmake --build build -j"$J"
    # PACKAGE_MODE=OFF lays the program out as a bundle under build/bin: binary beside resources.
    mkdir -p AppDir/usr/bin
    cp -a build/bin/. AppDir/usr/bin/
    BIN=AppDir/usr/bin/pcsx2-qt
    DESKTOP=src/.github/workflows/scripts/linux/pcsx2-qt.desktop
    ICON=src/bin/resources/icons/AppIconLarge.png
    ;;
  cemu)
    # wxWidgets 3.3, GTK3 toolkit with OpenGL: Cemu's UI.
    dep wxWidgets https://github.com/wxWidgets/wxWidgets.git v3.3.1 \
      -DwxBUILD_TOOLKIT=gtk3 -DwxUSE_OPENGL=ON -DwxBUILD_SAMPLES=OFF -DwxBUILD_TESTS=OFF -DwxBUILD_DEMOS=OFF \
      -DwxUSE_WEBVIEW=OFF -DwxUSE_MEDIACTRL=OFF
    git clone -q --depth 1 https://github.com/cemu-project/Cemu.git src
    git -C src submodule update -q --init --recursive --depth 1
    cmake -S src -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_VCPKG=OFF -DENABLE_WAYLAND=ON \
      -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DwxWidgets_CONFIG_EXECUTABLE=/opt/deps/bin/wx-config
    cmake --build build -j"$J"
    mkdir -p AppDir/usr/bin AppDir/usr/share/Cemu
    cp -a src/bin/. AppDir/usr/share/Cemu/
    install -m755 src/bin/Cemu_release AppDir/usr/bin/Cemu 2>/dev/null || install -m755 build/bin/Cemu_release AppDir/usr/bin/Cemu
    rm -f AppDir/usr/share/Cemu/Cemu_release
    BIN=AppDir/usr/bin/Cemu
    DESKTOP=src/dist/linux/info.cemu.Cemu.desktop
    ICON=src/dist/linux/info.cemu.Cemu.png
    ;;
  *) echo "unknown target $T"; exit 2 ;;
esac

# The desktop entry and icon appimagetool insists on, the icon named as the entry's Icon= line
# asks. Exec= must name the bundled binary, not a path.
ICONNAME=$(sed -n 's/^Icon=//p' "$DESKTOP" | head -1); ICONNAME=${ICONNAME:-$(basename "$BIN")}
install -Dm644 "$DESKTOP" "AppDir/usr/share/applications/$(basename "$DESKTOP")"
install -Dm644 "$ICON" "AppDir/usr/share/icons/hicolor/256x256/apps/$ICONNAME.png"
sed -i "s|^Exec=.*|Exec=$(basename "$BIN") %f|" "AppDir/usr/share/applications/$(basename "$DESKTOP")"

for tool in linuxdeploy linuxdeploy-plugin-qt; do
  curl -fsSL -o "/usr/local/bin/$tool" \
    "https://github.com/linuxdeploy/$tool/releases/download/continuous/$tool-aarch64.AppImage"
  chmod +x "/usr/local/bin/$tool"
done
export APPIMAGE_EXTRACT_AND_RUN=1 NO_STRIP=1 OUTPUT="$T.AppImage" LD_LIBRARY_PATH=/opt/deps/lib:/opt/deps/lib64
export QMAKE=/usr/bin/qmake6
# Qt's platform plugins by the names this Qt ships (6.10 merged the two wayland ones).
EXTRA_PLATFORM_PLUGINS=$(ls /usr/lib/qt6/plugins/platforms/ | grep -E '^libqwayland.*\.so$|^libqxcb\.so$' | paste -sd';')
export EXTRA_PLATFORM_PLUGINS
echo "== platform plugins: $EXTRA_PLATFORM_PLUGINS"
export EXTRA_QT_PLUGINS="svg;wayland-shell-integration;wayland-decoration-client;wayland-graphics-integration-client"
# Cemu is GTK (wxWidgets): linuxdeploy's gtk plugin looks for GTK's runtime data at Debian
# paths, finds nothing on Arch and copies '' - and the desktop this runs on installs gtk3
# anyway, so only the binary's own dependencies need bundling.
if [ "$T" = cemu ]; then
  # gdk-pixbuf's loaders and the schemas GTK reads at startup, which a bare deploy leaves out.
  for d in /usr/lib/gdk-pixbuf-2.0 /usr/share/glib-2.0/schemas; do
    [ -d "$d" ] && mkdir -p "AppDir$d" && cp -a "$d/." "AppDir$d/"
  done
  linuxdeploy --appdir AppDir -e "$BIN" -d "AppDir/usr/share/applications/$(basename "$DESKTOP")" \
    --output appimage
else
  linuxdeploy --appdir AppDir -e "$BIN" -d "AppDir/usr/share/applications/$(basename "$DESKTOP")" \
    --plugin qt --output appimage
fi
ls -l ./*.AppImage
sha256sum "$T.AppImage" | awk '{print $1}' > "$T.sha256"
