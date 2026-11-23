#!/usr/bin/env python3
"""Build the Community profiles catalog Bannerlator reads (release `input-controls`).

Input folder (--src):
  original/index.txt + original/*.icp   Winlator layouts by brunodev85 (LGPL-2.1), index.txt gives the order
  discord/discord.json + discord/*.icpx  layouts shared in #bannerlator-osc-sharing; discord.json lists
                                         title, file, author, date, note, link for each
Output folder (--out): every layout under its release asset name + index.json.
Upload the output folder's files to the `input-controls` release (gh release upload --clobber).

Usage: python3 tools/input_controls_index.py --src <dir> --out <dir>
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date


def asset_name(prefix, name):
    return prefix + re.sub(r'[^A-Za-z0-9._-]+', '_', name)


def layout_info(path):
    with open(path, 'rb') as f:
        raw = f.read()
    data = json.loads(raw.decode('utf-8'))
    elements = len(data.get('elements') or [])
    bindings = sum(len(c.get('controllerBindings') or []) for c in (data.get('controllers') or []))
    if elements and bindings:
        kind = 'both'
    elif bindings:
        kind = 'controller'
    elif elements:
        kind = 'on-screen'
    else:
        raise ValueError(f'{path}: no on-screen elements and no controller bindings')
    return {'type': kind, 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def add(out, src_path, asset, item, seen):
    if asset in seen:
        raise ValueError(f'duplicate asset name {asset}')
    seen.add(asset)
    shutil.copyfile(src_path, os.path.join(out, asset))
    item['file'] = asset
    item.update(layout_info(src_path))
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    seen = set()

    original_dir = os.path.join(args.src, 'original')
    with open(os.path.join(original_dir, 'index.txt'), encoding='utf-8') as f:
        names = [line.strip() for line in f if line.strip()]
    original = [add(args.out, os.path.join(original_dir, n), asset_name('original__', n),
                    {'title': os.path.splitext(n)[0], 'author': 'brunodev85'}, seen) for n in names]

    discord_dir = os.path.join(args.src, 'discord')
    with open(os.path.join(discord_dir, 'discord.json'), encoding='utf-8') as f:
        shared = json.load(f)
    discord = []
    for entry in shared['items']:
        item = {k: v for k, v in entry.items() if k != 'file'}
        discord.append(add(args.out, os.path.join(discord_dir, entry['file']),
                           asset_name('discord__', entry['file']), item, seen))

    index = {
        'schemaVersion': 1,
        'updated': date.today().isoformat(),
        'sections': [
            {'id': 'original', 'title': 'Original',
             'source': 'brunodev85/winlator input_controls (LGPL-2.1, asset LICENSE-LGPL-2.1.txt)',
             'items': original},
            {'id': 'discord', 'title': 'Discord shared', 'source': shared['source'], 'items': discord},
        ],
    }
    with open(os.path.join(args.out, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write('\n')
    license_src = os.path.join(original_dir, 'LICENSE-LGPL-2.1.txt')
    if os.path.isfile(license_src):
        shutil.copyfile(license_src, os.path.join(args.out, 'LICENSE-LGPL-2.1.txt'))
    print(f'index.json: {len(original)} original, {len(discord)} discord shared, {len(seen)} layout files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
