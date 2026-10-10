# Pakkeliste – Home Assistant integration

A packing list with a reusable template. Create a trip from the template, prune what you don't need, then check items off while packing. It adds a **Pakkeliste** panel to the Home Assistant sidebar (works in the mobile app too).

## Install

### HACS (custom repository)
1. HACS → ⋮ → Custom repositories → add `https://github.com/mikifp/hasspackinglist` as type **Integration**.
2. Download **Pakkeliste**, restart Home Assistant.

### Manual
Copy `custom_components/packing_list` into your Home Assistant `config/custom_components/` folder and restart.

### Set up
Settings → Devices & services → Add integration → **Pakkeliste**. The panel appears in the sidebar.

## Use
- **Skabelon** (template): edit categories and items. Write quantities as `Shorts (7)` or `Håndklæder x2`, or use the − / + buttons.
- **Turtyper** (Sommerhus, Badeferie, Sommerlejr): each item can belong to one or more trip types. A new trip only gets the items of the chosen type, or everything if you choose "Alt". The initial assignment is a guess per category, so adjust it in the template editor.
- **Ny tur**: copies the template. Use **Rediger** to remove items, change quantities or add one-off items. Then tap items to check them off. Everyone with access to Home Assistant can use the same trips, and the view refreshes every few seconds.

Data is stored in Home Assistant's `.storage/packing_list`, so it is included in backups. On first setup the template is seeded from `custom_components/packing_list/seed.py`.

## Development
```
pip install -r requirements_test.txt
pytest
```
