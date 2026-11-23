# Community control profiles

The list Bannerlator shows under Controls → Community profiles lives in the release
[`input-controls`](https://github.com/The412Banner/winlator-contents/releases/tag/input-controls).

| Asset | What |
|---|---|
| `index.json` | The catalog the app reads: sections `original` and `discord`, each item with title, author, file, type (`on-screen`, `controller`, `both`), size, sha256; Discord items also date, note (the poster's description) and link (the post) |
| `original__*.icp` | Winlator's layouts by [brunodev85](https://github.com/brunodev85/winlator/tree/main/input_controls), LGPL-2.1 (`LICENSE-LGPL-2.1.txt`) |
| `discord__*.icpx` | Layouts posted in the Discord channel #bannerlator-osc-sharing (BannerHub & Emulation server), credited by Discord display name |

Download URL of a file: `https://github.com/The412Banner/winlator-contents/releases/download/input-controls/<file>`.

## Sharing a layout

Export it in Bannerlator (Controls → the profile → Export) and post the `.icpx` file with a screenshot in #bannerlator-osc-sharing.

## Updating the catalog

1. Source folder: `original/` (Bruno's files + `index.txt` + `LICENSE-LGPL-2.1.txt`) and `discord/` (the shared files + `discord.json`
   with title, file, author, date, note, link per entry). Add the new file and its entry to `discord.json`.
2. `python3 tools/input_controls_index.py --src <source folder> --out <output folder>`
3. `gh release upload input-controls <output folder>/* --clobber -R The412Banner/winlator-contents`
