# proot, built from the Termux fork

These are **Android/bionic** binaries. They do not run inside the Linux runtime — they are what
*creates* it, so they execute on the Android side and travel in the rootfs tarball only because that
is how they reach a device without an app reinstall being able to replace them.

    proot             PRoot, aarch64, bionic — Termux fork v5.1.107.92
    loader            its freestanding loader (PROOT_LOADER)
    libtalloc.so.2    proot links against it; shipped under its SONAME, which is what the loader
                      asks for. A file called libtalloc.so is one it will never find.

⚠️ **These are Termux's published binaries, not our build — deliberately.** Our build of the same
fork starts fine but breaks GTK inside the runtime: the first icon a GTK client loads aborts the
process and takes the session with it (`Gtk:ERROR ... ensure_surface_for_gicon`, preceded by a
`bwrap` invocation). A/B on device, same rootfs, same app: ours aborts twice per session, Termux's
zero. The cause is that Termux builds with `PROOT_WITH_LIBANDROID_SHMEM=true` against
`libandroid-shmem`, routing System V shared memory — which Android does not have — through it.
`build-proot.yml` now does the same; **swap these for our own artifact once a build with that change
is verified on device.**

Built by `.github/workflows/build-proot.yml` from
<https://github.com/termux/proot> `v5.1.107.92` with the NDK, against Termux's own talloc, with
`RUNPATH $ORIGIN` so libtalloc is found beside proot. The copies here come from that workflow and
are refreshed from its artifact; they are checked in so the rootfs build does not depend on a
previous run. The workflow now also applies the patch set under `tools/proot/patches`
(`tools/proot/PATCHES.md`: DroidDeck's nine proot speed-ups, tracee lookup by pid, one-shot deep
path resolution, a seccomp filter that stops only for the arguments proot acts on); the copies
here predate it and stay Termux's until a patched artifact is proven on device.

## Why not `app/src/main/cpp/proot`

That tree is an old snapshot of upstream proot 5.1.0 and **cannot exec anything on a current
Android**: `proot error: execve(...): Bad address`. Bisected on device, the fault is in the binary
and not the loader — our loader paired with a working proot runs fine. Both report version "5.1.0",
because the fork keeps upstream's base version string, which is exactly why the two were assumed to
be the same code for far too long. The fork is thousands of lines ahead in the ptrace and exec core.

## Licence

PRoot is **GPL-2.0-or-later**, compatible with this project's GPL-3.0. libtalloc is
LGPL-3.0-or-later. Corresponding source:

  * <https://github.com/termux/proot> at tag `v5.1.107.92`
  * talloc as packaged by Termux:
    <https://github.com/termux/termux-packages/tree/master/packages/libtalloc>
