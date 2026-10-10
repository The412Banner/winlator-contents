#!/usr/bin/env python3
"""Records what a Windows installer leaves behind in a Wine prefix, without keeping the installer's files.

record.py --component NAME --installer FILE --out DIR [--recipes recipes.json] [--extract DIR]

A fresh 64-bit prefix is made, its files and registry noted, the installer run unattended (the
switches in recipes.json), and the prefix noted again. The difference is the recording:

  <out>/<component>.snapshot.json
      "files":    every file the installer placed under drive_c, with size and sha256, and where
                  the same bytes sit inside the installer when an extractor (innoextract, 7-Zip)
                  can reach them ("source"), so a device pulls them from the vendor's own
                  installer instead of a copy we host. A file the installer generated (no
                  matching bytes inside it) is carried inline when small ("data", base64), else
                  listed as "missing" for the recipe to deal with.
      "registry": every value the installer added or changed, in the shape droiddeck-wincomponents
                  writes into a prefix (hive, key, name, type, data), the user's folder rewritten
                  to Proton's steamuser and Wine's own bookkeeping left out.
  <out>/<component>.summary.md   a readable account of the run.

The point of the recording is the registry: a self-registering DLL (a DirectShow filter) decides
its own CLSID and filter entries at run time, so nothing but running it tells us what they are.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

INLINE_FILE_LIMIT = 256 * 1024
INLINE_TOTAL_LIMIT = 2 * 1024 * 1024

# Folders whose contents are the installer's own litter, not the product.
SKIP_DIRS = ("windows/temp", "windows/installer", "users/*/temp", "users/*/appdata/local/temp",
             "users/*/appdata/local/microsoft/windows/inetcache", "programdata/microsoft/windows/start menu",
             "users/*/appdata/roaming/microsoft/windows/start menu", "users/*/desktop", "users/*/start menu",
             "windows/logs", "windows/prefetch")
SKIP_FILE_SUFFIXES = (".log", ".lnk", ".url", ".tmp")

# Registry keys Wine or the prefix maintain by themselves between two snapshots.
SKIP_KEY_PREFIXES = (
    "software\\wine\\", "software\\microsoft\\windows\\currentversion\\explorer\\",
    "software\\microsoft\\windows nt\\currentversion\\profilelist", "system\\currentcontrolset\\control\\session manager\\environment\\",
    "software\\microsoft\\windows\\currentversion\\installer\\userdata", "software\\microsoft\\cryptography\\",
    "software\\microsoft\\windows\\currentversion\\shell extensions\\cached", "software\\classes\\local settings\\",
    "software\\microsoft\\windows\\currentversion\\explorer", "software\\microsoft\\rpc\\",
    "software\\microsoft\\windows nt\\currentversion\\fonts", "software\\microsoft\\windows nt\\currentversion\\winlogon",
    "control panel\\", "environment", "volatile environment", "software\\microsoft\\windows\\currentversion\\uninstall\\{",
    "console", "console\\",
)
SKIP_VALUE_NAMES = {"installdate", "installtime", "lastwritetime", "installsource", "sourcelist", "lastusedsource",
                    "estimatedsize", "modified", "installlocation"}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd, env=None, timeout=None, check=False):
    return subprocess.run(cmd, env=env, timeout=timeout, check=check, capture_output=True, text=True, errors="replace")


# ---------------------------------------------------------------- files

SKIP_DIR_PATTERNS = [re.compile("^" + re.escape(p).replace("\\*", "[^/]+") + "(/|$)") for p in SKIP_DIRS]


def skipped_path(rel):
    lower = rel.lower()
    return lower.endswith(SKIP_FILE_SUFFIXES) or any(pattern.match(lower) for pattern in SKIP_DIR_PATTERNS)


def snapshot_files(drive_c):
    found = {}
    for root, dirs, files in os.walk(drive_c):
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                continue
            rel = path.relative_to(drive_c).as_posix()
            if skipped_path(rel):
                continue
            try:
                found[rel] = (path.stat().st_size, sha256_of(path))
            except OSError:
                continue
    return found


# ---------------------------------------------------------------- registry

def unescape(text):
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "x" and i + 5 < len(text):
                try:
                    out.append(chr(int(text[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            out.append({"n": "\n", "r": "\r", "0": "\0", "t": "\t"}.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_reg(path):
    """A Wine registry file as {key: {name: raw}}; name "" is the default value; a key with no
    values is {}. Multi-line hex values are joined."""
    keys = {}
    current = None
    pending = None
    try:
        lines = Path(path).read_text("utf-8", errors="replace").split("\n")
    except FileNotFoundError:
        return keys
    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if pending is not None:
            pending += line.strip()
            if pending.endswith("\\"):
                pending = pending[:-1]
                continue
            name, raw = pending_name, pending
            keys[current][name] = raw
            pending = None
            continue
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("["):
            end = line.rfind("]")
            key = line[1:end].replace("\\\\", "\\")
            current = key
            keys.setdefault(current, {})
            continue
        if current is None:
            continue
        if line.startswith("@="):
            name, raw = "", line[2:]
        elif line.startswith('"'):
            end = 1
            while end < len(line):
                if line[end] == "\\":
                    end += 2
                    continue
                if line[end] == '"':
                    break
                end += 1
            name = unescape(line[1:end])
            raw = line[end + 2:] if line[end + 1:end + 2] == "=" else ""
        else:
            continue
        if raw.endswith("\\"):
            pending, pending_name = raw[:-1], name
            continue
        keys[current][name] = raw
    return keys


def decode(raw):
    """A Wine registry value as (type, data) in droiddeck-wincomponents' vocabulary, or None."""
    if raw.startswith('"') and raw.endswith('"'):
        return "sz", unescape(raw[1:-1])
    if raw.startswith("dword:"):
        try:
            return "dword", int(raw[6:], 16)
        except ValueError:
            return None
    if raw.startswith("str(2):") or raw.startswith("str(7):"):
        text = unescape(raw[7:].strip('"'))
        return ("expand_sz", text) if raw.startswith("str(2)") else ("multi_sz", [s for s in text.split("\0") if s])
    match = re.match(r"hex(\((\d+)\))?:(.*)$", raw)
    if match:
        kind = int(match.group(2) or 3)
        data = bytes.fromhex(match.group(3).replace(",", "").replace("\\", ""))
        if kind in (2, 7, 1):
            text = data.decode("utf-16-le", errors="replace")
            if kind == 7:
                return "multi_sz", [s for s in text.split("\0") if s]
            return ("expand_sz" if kind == 2 else "sz"), text.rstrip("\0")
        if kind == 4 and len(data) == 4:
            return "dword", int.from_bytes(data, "little")
        return "binary", data.hex()
    return None


def skipped_key(key):
    lower = key.lower()
    return any(lower.startswith(prefix) or lower == prefix.rstrip("\\") for prefix in SKIP_KEY_PREFIXES) or "\\volatile" in lower


def diff_registry(before, after, hive, home_user):
    """The values in [after] that [before] lacks or has differently, as registry.json entries."""
    entries = []
    home_pattern = re.compile(re.escape("C:\\users\\" + home_user), re.IGNORECASE) if home_user else None
    for key, values in after.items():
        if skipped_key(key):
            continue
        old = before.get(key)
        if old is None and not values:
            entries.append({"hive": hive, "key": key, "type": "key"})
            continue
        for name, raw in values.items():
            if name.lower() in SKIP_VALUE_NAMES:
                continue
            if old is not None and old.get(name) == raw:
                continue
            decoded = decode(raw)
            if decoded is None:
                continue
            kind, data = decoded
            if isinstance(data, str):
                if "Z:\\" in data or "z:\\" in data:
                    continue
                if home_pattern:
                    data = home_pattern.sub("C:\\\\users\\\\steamuser", data)
            elif isinstance(data, list) and home_pattern:
                data = [home_pattern.sub("C:\\\\users\\\\steamuser", item) for item in data]
            entries.append({"hive": hive, "key": key, "name": name, "type": kind, "data": data})
    return entries


# ---------------------------------------------------------------- 32-bit recordings in the 64-bit layout

# A 32-bit installer that refuses a 64-bit prefix (.NET 2.0 and 3.5, Jet) is recorded in a win32
# prefix, then translated into what the same installer leaves on 64-bit Windows: files move the
# way the file-system redirector moves them (system32 -> syswow64, Program Files -> Program
# Files (x86)), and the registry is replayed into a fresh 64-bit prefix through Wine's own 32-bit
# regedit, so Wine's WOW64 registry redirection (Wow6432Node, the Classes subkeys) decides where
# each key lands rather than a hand-written table.
SYSTEM32_SHARED = ("catroot", "catroot2", "driverstore", "drivers", "etc", "logfiles", "spool")


def remap_file(rel):
    parts = rel.split("/")
    lower = [p.lower() for p in parts]
    if lower[:2] == ["windows", "system32"] and not (len(lower) > 2 and lower[2] in SYSTEM32_SHARED):
        return "/".join(["windows", "syswow64"] + parts[2:])
    if lower[:1] == ["program files"]:
        return "/".join(["Program Files (x86)"] + parts[1:])
    if lower[:2] == ["programdata", "microsoft"] or lower[:1] == ["users"]:
        return rel
    return rel


def reg_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def encode_value(kind, data):
    if kind == "sz":
        return '"%s"' % reg_escape(data)
    if kind == "dword":
        return "dword:%08x" % int(data)
    if kind == "expand_sz":
        return "hex(2):" + ",".join("%02x" % b for b in (data + "\0").encode("utf-16-le"))
    if kind == "multi_sz":
        return "hex(7):" + ",".join("%02x" % b for b in ("\0".join(list(data) + [""]) + "\0").encode("utf-16-le"))
    if kind == "binary":
        return "hex:" + ",".join(data[i:i + 2] for i in range(0, len(data), 2))
    return None


def write_reg(entries, path):
    """The recorded values as a .reg file regedit imports (UTF-16, as Windows writes them)."""
    roots = {"HKLM": "HKEY_LOCAL_MACHINE", "HKCU": "HKEY_CURRENT_USER"}
    lines = ["Windows Registry Editor Version 5.00", ""]
    by_key = {}
    for entry in entries:
        by_key.setdefault((entry["hive"], entry["key"]), []).append(entry)
    for (hive, key), values in by_key.items():
        lines.append("[%s\\%s]" % (roots[hive], key))
        for entry in values:
            if entry.get("type") == "key":
                continue
            raw = encode_value(entry["type"], entry["data"])
            if raw is None:
                continue
            lines.append(("@=%s" if entry["name"] == "" else '"%s"=%%s' % reg_escape(entry["name"])) % raw if entry["name"] else "@=" + raw)
        lines.append("")
    Path(path).write_text("\n".join(lines) + "\n", "utf-16")


def replay_into_win64(entries, work, home_user, notes):
    """Imports the 32-bit recording's registry into a fresh 64-bit prefix with Wine's 32-bit
    regedit and records what landed, Wow6432Node and all."""
    prefix = work / "pfx64"
    env = wine_env(prefix, "win64", "")
    print("== making a fresh win64 prefix to replay the registry into", flush=True)
    result = run(["wineboot", "-u"], env=env, timeout=600)
    wait_wine(env, 300)
    if result.returncode != 0:
        notes.append("the 64-bit replay prefix could not be made; registry left in the 32-bit layout")
        return entries
    before = {"HKLM": parse_reg(prefix / "system.reg"), "HKCU": parse_reg(prefix / "user.reg")}
    reg_file = work / "recording.reg"
    write_reg(entries, reg_file)
    dos_path = "Z:" + str(reg_file.resolve()).replace("/", "\\")
    result = run(["wine", "C:\\windows\\syswow64\\regedit.exe", "/S", dos_path], env=env, timeout=600)
    wait_wine(env, 300)
    subprocess.run(["wineserver", "-k"], env=env)
    time.sleep(2)
    if result.returncode != 0:
        notes.append("32-bit regedit import exit %s: %s" % (result.returncode, result.stderr.strip()[-300:]))
    after = {"HKLM": parse_reg(prefix / "system.reg"), "HKCU": parse_reg(prefix / "user.reg")}
    replayed = diff_registry(before["HKLM"], after["HKLM"], "HKLM", home_user) + \
        diff_registry(before["HKCU"], after["HKCU"], "HKCU", home_user)
    # Only what the recording wrote: Wine stirs a few keys of its own in a fresh prefix meanwhile.
    wanted = {(e["hive"], e["key"].lower()) for e in entries}
    def recorded_key(e):
        plain = e["key"].lower().replace("\\wow6432node", "")
        return (e["hive"], plain) in wanted or (e["hive"], e["key"].lower()) in wanted
    replayed = [e for e in replayed if recorded_key(e)]
    wow = sum(1 for e in replayed if "wow6432node" in e["key"].lower())
    notes.append("registry replayed through Wine's 32-bit regedit into a 64-bit prefix: %d values in, %d out, %d under Wow6432Node" % (
        sum(1 for e in entries if e.get("type") != "key"), sum(1 for e in replayed if e.get("type") != "key"), wow))
    print("   replay: %d values in, %d out, %d under Wow6432Node" % (len(entries), len(replayed), wow), flush=True)
    return replayed


# ---------------------------------------------------------------- the run

def wine_env(prefix, arch, overrides):
    env = dict(os.environ)
    env.update({"WINEPREFIX": str(prefix), "WINEARCH": arch, "WINEDEBUG": "-all",
                "WINEDLLOVERRIDES": "winemenubuilder.exe=d" + (";" + overrides if overrides else "")})
    env.pop("DISPLAY", None)
    return env


def wait_wine(env, timeout):
    try:
        subprocess.run(["wineserver", "-w"], env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["wineserver", "-k"], env=env)
        time.sleep(3)


NESTED_SUFFIXES = (".7z", ".zip", ".cab", ".exe", ".msi", ".rar", ".xz", ".gz", ".tar")


def open_nested(dest, depth=0):
    """Archives inside an extraction (K-Lite carries its filters as 7-Zip payloads) are opened in
    place, one folder per archive, two levels deep."""
    if depth > 1 or not shutil.which("7z"):
        return 0
    opened = 0
    for path in sorted(p for p in dest.rglob("*") if p.is_file() and p.suffix.lower() in NESTED_SUFFIXES):
        if path.name.endswith(".nested") or path.stat().st_size < 1024:
            continue
        probe = run(["7z", "l", "-ba", str(path)], timeout=300)
        if probe.returncode != 0 or not probe.stdout.strip():
            continue
        folder = path.with_name(path.name + ".nested")
        folder.mkdir(exist_ok=True)
        run(["7z", "x", "-y", "-bd", "-bso0", "-bsp0", "-o" + str(folder), str(path)], timeout=1800)
        if any(folder.rglob("*")):
            opened += 1 + open_nested(folder, depth + 1)
        else:
            shutil.rmtree(folder, ignore_errors=True)
    return opened


def extract_installer(installer, dest, notes):
    """Opens the installer with innoextract or 7-Zip; returns {sha256: relative path} of what came out."""
    found = {}
    tried = []
    if shutil.which("innoextract"):
        tried.append("innoextract")
        listing = run(["innoextract", "-l", str(installer)], timeout=600)
        said = (listing.stderr + listing.stdout).strip().splitlines()
        warnings = [line for line in said if "warning" in line.lower() or "error" in line.lower()]
        print("   innoextract: %d listed, %s" % (sum(1 for line in said if line.startswith(" - ")), "; ".join(warnings[:3]) or "no warnings"), flush=True)
        if warnings:
            notes.append("innoextract: " + "; ".join(warnings[:3]))
        result = run(["innoextract", "-q", "-m", "-d", str(dest), str(installer)], timeout=1800)
        if result.returncode != 0 or not any(dest.rglob("*")):
            notes.append("innoextract extracted nothing (exit %s)" % result.returncode)
            shutil.rmtree(dest, ignore_errors=True)
            dest.mkdir(parents=True, exist_ok=True)
    if not any(dest.rglob("*")) and shutil.which("7z"):
        tried.append("7z")
        result = run(["7z", "x", "-y", "-bd", "-bso0", "-bsp0", "-o" + str(dest), str(installer)], timeout=1800)
        if not any(dest.rglob("*")):
            notes.append("7-Zip extracted nothing (exit %s)" % result.returncode)
    top = sum(1 for p in dest.rglob("*") if p.is_file())
    nested = open_nested(dest)
    for path in dest.rglob("*"):
        if path.is_file():
            found.setdefault(sha256_of(path), path.relative_to(dest).as_posix())
    print("   extraction: %d files at the top, %d nested archives opened, %d files in all" % (top, nested, len(found)), flush=True)
    notes.append("extraction: %d files, %d nested archives opened (%s)" % (len(found), nested, ", ".join(tried) or "no extractor"))
    return found, tried


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", required=True)
    parser.add_argument("--installer", help="the installer file (single-installer recipes)")
    parser.add_argument("--installers-dir", help="folder holding every recipe's installer assets by name")
    parser.add_argument("--out", required=True)
    parser.add_argument("--recipes", default=str(Path(__file__).with_name("recipes.json")))
    parser.add_argument("--extract", help="where the installer's own extraction goes (default: a temp dir)")
    args = parser.parse_args()

    recipes = json.loads(Path(args.recipes).read_text("utf-8"))
    recipe = recipes.get(args.component)
    if not recipe:
        print("no recipe for %s" % args.component, file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arch = recipe.get("arch", "win64")
    timeout = int(recipe.get("timeout", 600))
    notes = []
    assets = Path(args.installers_dir).resolve() if args.installers_dir else None

    def runs_of(name):
        """A recipe's installers as (path, args) pairs, from --installers-dir or --installer."""
        r = recipes[name]
        items = r.get("installers") or [{"asset": r.get("installer"), "args": r.get("args", [])}]
        found = []
        for item in items:
            path = assets / item["asset"] if assets else Path(args.installer).resolve()
            if not path.is_file():
                raise SystemExit("installer missing: %s" % path)
            found.append((path, list(item.get("args", []))))
        return found

    def run_installer(path, run_args, limit, label):
        print("== running %s %s" % (path.name, " ".join(run_args)), flush=True)
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", "wine", str(path)] + run_args
        started_at = time.time()
        try:
            result = run(cmd, env=env, timeout=limit)
            exit_code = result.returncode
            if result.stderr.strip():
                notes.append("%s stderr: %s" % (label, result.stderr.strip()[-400:]))
        except subprocess.TimeoutExpired:
            exit_code = "timeout"
            notes.append("%s was still running after %d s and was killed" % (label, limit))
        wait_wine(env, 180)
        subprocess.run(["wineserver", "-k"], env=env)
        time.sleep(2)
        took = int(time.time() - started_at)
        print("== %s exit %s after %d s" % (label, exit_code, took), flush=True)
        if exit_code != 0:
            # What the installer itself said: Microsoft's setups leave dd_*.txt / *.log in Temp.
            logs = []
            for pattern in ("users/*/Temp/*.txt", "users/*/Temp/*.log", "users/*/Temp/*/*.txt", "users/*/Temp/*/*.log",
                            "windows/temp/*.txt", "windows/temp/*.log", "windows/temp/*/*.log", "*/*.log", "*/*.txt"):
                for log in drive_c.glob(pattern):
                    try:
                        if log.stat().st_mtime >= started_at - 5 and log.stat().st_size > 0:
                            logs.append(log)
                    except OSError:
                        pass
            logs = sorted(set(logs), key=lambda l: -l.stat().st_size)[:3]
            for log in logs:
                try:
                    text = log.read_bytes().decode("utf-16", errors="replace") if log.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") else log.read_text("utf-8", errors="replace")
                except OSError:
                    continue
                tail = "\n".join(line for line in text.splitlines() if line.strip())[-1500:]
                print("   -- %s (last lines) --\n%s" % (log.relative_to(drive_c), tail), flush=True)
                notes.append("%s log %s: %s" % (label, log.relative_to(drive_c).as_posix(), tail[-600:]))
                # The lines that name the problem, wherever they are in the log.
                telling = [line.strip() for line in text.splitlines()
                           if re.search(r"block|gencomp|return value 3|error|fail|not (met|found|supported)|requires|missing", line, re.IGNORECASE)
                           and "does not match requested set" not in line][:25]
                if telling:
                    print("   -- %s (telling lines) --\n%s" % (log.relative_to(drive_c), "\n".join(telling)), flush=True)
        return exit_code, took

    runs = runs_of(args.component)
    installer = runs[0][0]

    work = Path(tempfile.mkdtemp(prefix="snapshot-"))
    prefix = work / "pfx"
    env = wine_env(prefix, arch, recipe.get("dll_overrides", ""))
    print("== making a fresh %s prefix" % arch, flush=True)
    result = run(["wineboot", "-u"], env=env, timeout=600)
    wait_wine(env, 300)
    if result.returncode != 0:
        print(result.stderr[-800:], file=sys.stderr)
        return 1
    wine_version = run(["wine", "--version"], env=env).stdout.strip()
    drive_c = prefix / "drive_c"
    home_user = next((p.name for p in (drive_c / "users").iterdir() if p.is_dir() and p.name.lower() not in ("public", "default")), "")
    # The Windows version the installer wants to see (MDAC refuses anything after 2000), set before
    # the first snapshot so it is not recorded; prerequisites likewise, so a service pack records its delta.
    winver = recipe.get("winver")
    if winver:
        run(["wine", "reg", "add", "HKCU\\Software\\Wine", "/v", "Version", "/d", winver, "/f"], env=env, timeout=300)
        wait_wine(env, 120)
        notes.append("recorded with the Windows version set to %s" % winver)
    for key in recipe.get("pre_reg_delete", []):
        run(["wine", "reg", "delete", key, "/f"], env=env, timeout=300)
        wait_wine(env, 120)
        notes.append("deleted %s before recording" % key)
    for prerequisite in recipe.get("after", []):
        for path, run_args in runs_of(prerequisite):
            run_installer(path, run_args, int(recipes[prerequisite].get("timeout", 600)), "prerequisite " + prerequisite)
        notes.append("recorded on top of %s" % prerequisite)

    print("== noting the prefix before", flush=True)
    files_before = snapshot_files(drive_c)
    reg_before = {"HKLM": parse_reg(prefix / "system.reg"), "HKCU": parse_reg(prefix / "user.reg")}

    status, elapsed = None, 0
    if recipe.get("extract_to"):
        # No silent mode (dirac's NSIS wizard): unpack the installer where its wizard would have put
        # the files and register the filters it would have registered, with Wine's own regsvr32.
        target = drive_c / recipe["extract_to"]
        target.mkdir(parents=True, exist_ok=True)
        started_at = time.time()
        result = run(["7z", "x", "-y", "-bso0", "-bsp0", "-o" + str(target), str(installer)], timeout=600)
        for litter in ("$PLUGINSDIR", "$TEMP", "$R0"):
            shutil.rmtree(target / litter, ignore_errors=True)
        status = result.returncode
        notes.append("unpacked into %s instead of running the wizard (no silent mode)" % recipe["extract_to"])
        for rel in recipe.get("register", []):
            dos = "C:\\" + rel.replace("/", "\\")
            print("== regsvr32 %s" % dos, flush=True)
            result = run(["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", "wine", "regsvr32", "/s", dos], env=env, timeout=300)
            wait_wine(env, 120)
            notes.append("regsvr32 %s exit %s" % (rel, result.returncode))
            if result.returncode != 0 and status == 0:
                status = result.returncode
        subprocess.run(["wineserver", "-k"], env=env)
        time.sleep(2)
        elapsed = int(time.time() - started_at)
        print("== %s unpacked and registered, exit %s after %d s" % (installer.name, status, elapsed), flush=True)
    else:
        for path, run_args in runs:
            exit_code, took = run_installer(path, run_args, timeout, path.name)
            elapsed += took
            status = exit_code if status in (None, 0) else status

    print("== noting the prefix after", flush=True)
    files_after = snapshot_files(drive_c)
    reg_after = {"HKLM": parse_reg(prefix / "system.reg"), "HKCU": parse_reg(prefix / "user.reg")}

    placed = {rel: info for rel, info in files_after.items() if files_before.get(rel) != info}
    removed = sorted(rel for rel in files_before if rel not in files_after)
    registry = diff_registry(reg_before["HKLM"], reg_after["HKLM"], "HKLM", home_user) + \
        diff_registry(reg_before["HKCU"], reg_after["HKCU"], "HKCU", home_user)

    # Where each recorded file is read from in the recording prefix (differs from its recorded
    # path once a 32-bit recording is moved into the 64-bit layout).
    source_of = {rel: rel for rel in placed}
    layout = arch
    if arch == "win32" and recipe.get("remap", True) and (placed or registry):
        moved = {}
        for rel, info in placed.items():
            target = remap_file(rel)
            moved[target] = info
            source_of[target] = rel
        shifted = sum(1 for rel in placed if remap_file(rel) != rel)
        placed = moved
        removed = [remap_file(rel) for rel in removed]
        # The strings the installer wrote point where it put the files; on 64-bit Windows a 32-bit
        # installer resolves "Program Files" to "Program Files (x86)" and writes that. (system32
        # may stay: the file-system redirector sends a 32-bit reader to syswow64 by itself.)
        program_files = re.compile(r"([A-Za-z]:\\)Program Files\\(?!\(x86\))", re.IGNORECASE)
        rewritten = 0
        for entry in registry:
            data = entry.get("data")
            if isinstance(data, str):
                new = program_files.sub(r"\1Program Files (x86)\\", data)
            elif isinstance(data, list):
                new = [program_files.sub(r"\1Program Files (x86)\\", item) for item in data]
            else:
                continue
            if new != data:
                entry["data"] = new
                rewritten += 1
        if rewritten:
            notes.append("%d registry strings now say Program Files (x86)" % rewritten)
        registry = replay_into_win64(registry, work, home_user, notes)
        notes.append("32-bit recording laid out as on 64-bit Windows: %d of %d files moved (syswow64, Program Files (x86))" % (shifted, len(placed)))
        layout = "win64"

    print("== opening the installer to find the placed files inside it", flush=True)
    extract_dir = Path(args.extract) if args.extract else work / "x"
    extract_dir.mkdir(parents=True, exist_ok=True)
    inside, tried = {}, []
    for index, (path, _) in enumerate(runs):
        folder = extract_dir / ("installer%d" % index) if len(runs) > 1 else extract_dir
        folder.mkdir(parents=True, exist_ok=True)
        found, used = extract_installer(path, folder, notes)
        for digest, rel in found.items():
            inside.setdefault(digest, (("installer%d/" % index) if len(runs) > 1 else "") + rel)
        tried = tried or used

    # When the installer cannot be opened (Inno Setup newer than innoextract reads, K-Lite) and
    # the recipe says its contents may be redistributed, the placed files travel as an archive
    # beside the recording instead of being pulled from the installer on the device.
    host_files = bool(recipe.get("host_files")) and bool(placed)
    files_archive = None
    if not placed:
        notes.append("the installer placed no files (exit %s): nothing to lay out" % status)
    if host_files:
        archive = out / ("%s.files.tar.xz" % args.component)
        with tempfile.TemporaryDirectory(prefix="files-") as staging:
            for rel in placed:
                target = Path(staging) / "drive_c" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(drive_c / source_of[rel], target)
            run(["tar", "-C", staging, "-cJf", str(archive), "drive_c"], timeout=1800, check=True)
        files_archive = {"name": archive.name, "size": archive.stat().st_size, "sha256": sha256_of(archive),
                         "licence": recipe.get("licence", "")}
        print("   files archive: %s (%d bytes)" % (archive.name, files_archive["size"]), flush=True)
    files, inline_total, missing = [], 0, 0
    for rel in sorted(placed):
        size, digest = placed[rel]
        entry = {"path": rel, "size": size, "sha256": digest}
        if host_files:
            entry["archived"] = True
        elif digest in inside:
            entry["source"] = inside[digest]
        elif size <= INLINE_FILE_LIMIT and inline_total + size <= INLINE_TOTAL_LIMIT:
            entry["data"] = base64.b64encode((drive_c / source_of[rel]).read_bytes()).decode("ascii")
            inline_total += size
        else:
            entry["missing"] = True
            missing += 1
        files.append(entry)

    snapshot = {
        "schema": 1,
        "component": args.component,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wine": wine_version, "arch": arch, "layout": layout,
        "installer": {"name": installer.name, "size": installer.stat().st_size, "sha256": sha256_of(installer),
                      "args": runs[0][1], "exit": status, "seconds": elapsed, "extractors": tried},
        "installers": [{"name": path.name, "size": path.stat().st_size, "sha256": sha256_of(path), "args": run_args} for path, run_args in runs],
        "after": recipe.get("after", []), "winver": winver,
        "stats": {"files": len(files), "from_installer": sum(1 for f in files if "source" in f),
                  "inline": sum(1 for f in files if "data" in f), "archived": sum(1 for f in files if f.get("archived")),
                  "missing": missing, "removed": len(removed), "registry": len(registry)},
        "files_archive": files_archive,
        "files": files, "removed": removed, "registry": registry, "notes": notes,
    }
    (out / ("%s.snapshot.json" % args.component)).write_text(json.dumps(snapshot, indent=1), "utf-8")

    by_hive = {}
    for value in registry:
        by_hive.setdefault(value["hive"], set()).add(value["key"].split("\\")[0] + "\\" + value["key"].split("\\")[1] if "\\" in value["key"] else value["key"])
    summary = ["# %s" % args.component, "",
               "Recorded %s on %s (%s prefix%s). Installer `%s`, exit %s after %d s." % (
                   snapshot["recorded"], wine_version, arch, ", laid out for win64" if layout != arch else "", installer.name, status, elapsed), "",
               "| | |", "|---|---|",
               "| files placed | %d |" % len(files),
               "| of which found inside the installer | %d |" % snapshot["stats"]["from_installer"],
               "| carried in the files archive beside this recording | %d |" % snapshot["stats"]["archived"],
               "| carried inline (generated, small) | %d |" % snapshot["stats"]["inline"],
               "| missing (generated, large) | %d |" % missing,
               "| files removed | %d |" % len(removed),
               "| registry values | %d |" % len(registry), "",
               "## Where the files went", ""]
    folders = {}
    for entry in files:
        top = "/".join(entry["path"].split("/")[:3])
        folders[top] = folders.get(top, 0) + 1
    summary += ["- `%s` · %d" % (top, n) for top, n in sorted(folders.items(), key=lambda item: -item[1])[:25]]
    summary += ["", "## Registry keys touched (top two levels)", ""]
    for hive, keys in sorted(by_hive.items()):
        for key in sorted(keys)[:40]:
            summary.append("- %s\\%s" % (hive, key))
    if missing:
        summary += ["", "## Missing (not inside the installer, too large to carry)", ""]
        summary += ["- `%s` (%d bytes)" % (f["path"], f["size"]) for f in files if f.get("missing")][:50]
    if notes:
        summary += ["", "## Notes", ""] + ["- " + n for n in notes]
    (out / ("%s.summary.md" % args.component)).write_text("\n".join(summary) + "\n", "utf-8")
    print("\n".join(summary[:12]), flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
