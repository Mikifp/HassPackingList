# Pakkeliste – Home Assistant add-on

A packing list with a reusable template. Create a trip from the template, prune what you don't need, then check items off while packing.

## Install
1. Home Assistant → Settings → Add-ons → Add-on store → ⋮ → Repositories.
2. Add `https://github.com/mikifp/hasspackinglist`.
3. Install **Pakkeliste**, start it and enable "Show in sidebar".

## Use
- **Skabelon** (template): edit categories and items. Write quantities as `Shorts (7)` or `Håndklæder x2`, or use the − / + buttons.
- **Turtyper** (Sommerhus, Badeferie, Sommerlejr): each item can belong to one or more trip types. A new trip only gets the items of the chosen type, or everything if you choose "Alt". The initial assignment is a guess per category, so adjust it in the template editor.
- **Ny tur**: copies the template. Use **Rediger** to remove items, change quantities or add one-off items. Then tap items to check them off. Several people can use the same trip, and it refreshes every few seconds.

Data is stored in `/data/packing.json` inside the add-on, so it is included in Home Assistant backups. On first start the template is seeded from `packing_list/seed.py`.

## Local development
```
DATA_DIR=./data PORT=8099 python3 packing_list/server.py
```
Standard library only, no dependencies.
