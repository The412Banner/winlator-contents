#!/usr/bin/env python3
"""DT_NEEDED audit of a Linux runtime and the Steam client installed in it.

  needed.py <rootfs> <steam root>

Parses every ELF under the runtime's program and library directories and the client's, and prints
each shared-object name nothing provides, with the files that ask for it. Runs on a device against
an installed runtime without proot, using the runtime's own python natively:

  R=/data/user/0/<pkg>/files/linuxfs
  PYTHONHOME=$R/usr $R/usr/lib/ld-linux-aarch64.so.1 --library-path $R/usr/lib $R/usr/bin/python3 -I needed.py $R $R/root/.local/share/Steam

Found r10's two Steam gaps (libibus-1.0.so.5 for steamwebhelper, libva.so.2 for steamui.so's
libavcodec) after the loader-based check in build-base.sh had passed.
"""
import os, struct, sys
R = sys.argv[1]; STEAM = sys.argv[2]
libdirs = [R+'/usr/lib', R+'/usr/local/lib', R+'/usr/lib/pulseaudio', R+'/usr/lib/gamescope',
           STEAM+'/steamrtarm64', STEAM+'/linuxarm64', STEAM+'/steamrtarm64/steam-runtime-heavy/lib']
avail = set()
for d in libdirs:
    if os.path.isdir(d):
        avail.update(os.listdir(d))
def needed(path):
    try:
        f = open(path, 'rb'); h = f.read(64)
    except Exception: return None
    if h[:4] != b'\x7fELF' or h[4] != 2 or h[5] != 1: return None
    phoff, = struct.unpack_from('<Q', h, 32); phentsize, phnum = struct.unpack_from('<HH', h, 54)
    f.seek(phoff); ph = f.read(phentsize * phnum)
    loads, dyn = [], None
    for i in range(phnum):
        t, fl, off, va, pa, fsz, msz, al = struct.unpack_from('<IIQQQQQQ', ph, i * phentsize)
        if t == 1: loads.append((va, off, fsz))
        if t == 2: dyn = (off, fsz)
    if not dyn: return []
    f.seek(dyn[0]); d = f.read(dyn[1])
    ents = [struct.unpack_from('<qQ', d, i) for i in range(0, len(d) - 15, 16)]
    strtab = next((v for t, v in ents if t == 5), None)
    if strtab is None: return []
    off = None
    for va, o, fsz in loads:
        if va <= strtab < va + fsz: off = o + (strtab - va); break
    if off is None: return []
    out = []
    for t, v in ents:
        if t == 1:
            f.seek(off + v); s = b''
            while True:
                c = f.read(64); s += c
                if b'\0' in c or not c: break
            out.append(s.split(b'\0')[0].decode(errors='replace'))
    return out
scan = [R+'/usr/bin', R+'/usr/local/bin', R+'/usr/lib', R+'/usr/local/lib', R+'/usr/lib/pulseaudio', R+'/usr/lib/gamescope',
        R+'/usr/lib/gstreamer-1.0', R+'/usr/lib/gio/modules', R+'/usr/lib/dri', STEAM+'/steamrtarm64', STEAM+'/linuxarm64',
        STEAM+'/steamrtarm64/steam-runtime-heavy/lib', STEAM+'/steamrtarm64/steam-runtime-heavy/bin', STEAM+'/steamrtarm64/steam-runtime-heavy/lib/aarch64-linux-gnu']
missing = {}
n = 0
for d in scan:
    if not os.path.isdir(d): continue
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if not os.path.isfile(p) or os.path.islink(p): continue
        ns = needed(p)
        if ns is None: continue
        n += 1
        for s in ns:
            if s not in avail:
                missing.setdefault(s, []).append(p.replace(R + '/', '').replace(STEAM + '/', 'STEAM/'))
print('scanned', n, 'ELF files;', len(missing), 'missing sonames')
for s, users in sorted(missing.items(), key=lambda kv: -len(kv[1])):
    print('%-40s %3d  e.g. %s' % (s, len(users), ' '.join(users[:3])))
