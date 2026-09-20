#!/bin/bash
# Builds one hosted package for the SteamDeck app's Linux runtime: the closure of a seed list over
# Arch Linux ARM's aarch64 repositories, minus every package the runtime image already carries, as
# a zstd tarball that extracts over the rootfs. Same closure and extraction as Bannerlator's
# build-linuxfs.sh, for the same rootfs.
#
#   desktop/build-pkg.sh <name> <seeds file> <base packages file> <out dir>
#
# Needs curl, tar, zstd, python3.
set -euo pipefail
name=${1:?package name}; seeds=${2:?seeds file}; base=${3:?base packages file}; out=${4:?out dir}
here=$(cd "$(dirname "$0")" && pwd)
mirror=http://mirror.archlinuxarm.org/aarch64
work=$(mktemp -d); mkdir -p "$out" "$work/db" "$work/pkgs" "$work/root"

for repo in core extra alarm; do
  curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "$work/db/$repo.db" "$mirror/$repo/$repo.db"
  mkdir -p "$work/db/x_$repo" && tar -xzf "$work/db/$repo.db" -C "$work/db/x_$repo"
done

mapfile -t seed_list < <(grep -vE '^\s*(#|$)' "$seeds")
python3 - "$work" "$base" "${seed_list[@]}" > "$work/pkglist.txt" <<'PY'
import os, sys, collections
work, basefile, seeds = sys.argv[1], sys.argv[2], sys.argv[3:]
base = set(l.strip() for l in open(basefile) if l.strip())
pkgs, provides = {}, collections.defaultdict(list)
def strip(d):
    for op in (">=", "<=", "==", ">", "<", "="):
        if op in d: return d.split(op)[0]
    return d
for repo in ("core", "extra", "alarm"):
    root = os.path.join(work, "db", "x_" + repo)
    for entry in os.listdir(root):
        fields, key = {}, None
        for fname in ("desc", "depends"):
            path = os.path.join(root, entry, fname)
            if not os.path.exists(path): continue
            for line in open(path, encoding="utf-8", errors="replace"):
                line = line.rstrip("\n")
                if line.startswith("%") and line.endswith("%"): key = line.strip("%"); fields[key] = []
                elif line == "": key = None
                elif key: fields[key].append(line)
        n = fields.get("NAME", [None])[0]
        if not n: continue
        rec = {"repo": repo, "file": fields["FILENAME"][0],
               "depends": [strip(d) for d in fields.get("DEPENDS", [])],
               "provides": [strip(p) for p in fields.get("PROVIDES", [])]}
        pkgs[n] = rec; provides[n].append(n)
        for p in rec["provides"]: provides[p].append(n)
seen, queue, missing = set(), list(seeds), []
while queue:
    want = queue.pop()
    real = want if want in pkgs else (provides.get(want) or [None])[0]
    if real is None: missing.append(want); continue
    if real in seen: continue
    seen.add(real)
    queue.extend(pkgs[real]["depends"])
if missing: sys.exit("unresolved: " + " ".join(missing))
# The runtime's own packages are not shipped twice: what r9 has, this package assumes.
for n in sorted(seen):
    if n in base: continue
    print(pkgs[n]["repo"] + "/" + pkgs[n]["file"])
PY
echo "$name: $(wc -l < "$work/pkglist.txt") packages beyond the runtime's own"

while read -r entry; do
  file=${entry#*/}
  curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o "$work/pkgs/$file" "$mirror/$entry"
  tar -tf "$work/pkgs/$file" >/dev/null
  tar -xf "$work/pkgs/$file" -C "$work/root" --no-same-owner --no-same-permissions \
    --exclude=.PKGINFO --exclude=.MTREE --exclude=.INSTALL --exclude=.BUILDINFO --exclude=.CHANGELOG
done < "$work/pkglist.txt"

# Our own files for this package (launchers, configs, wallpaper), if any.
if [ -d "$here/overlay-$name" ]; then cp -a "$here/overlay-$name/." "$work/root/"; fi
if [ -d "$here/overlay" ] && [ "$name" = desktop ]; then cp -a "$here/overlay/." "$work/root/"; fi

# Weight that no desktop on a phone reads.
rm -rf "$work/root/usr/share/doc" "$work/root/usr/share/man" "$work/root/usr/share/info" \
       "$work/root/usr/share/gtk-doc" "$work/root/usr/include" "$work/root/usr/lib/pkgconfig"
find "$work/root/usr/share/locale" -mindepth 1 -maxdepth 1 -type d ! -name 'en*' -exec rm -rf {} + 2>/dev/null || true
chmod -R u+rwX "$work/root"

sed 's#^[a-z]*/##' "$work/pkglist.txt" > "$out/$name.packages.txt"
tar -C "$work/root" --zstd -cf "$out/$name.tar.zst" .
sha256sum "$out/$name.tar.zst" | awk '{print $1}' > "$out/$name.sha256"
ls -l "$out/$name.tar.zst"
rm -rf "$work"
