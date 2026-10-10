"""Pakkeliste: a packing list with a reusable template, shown as a sidebar panel."""
from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import VIEWS
from .const import DOMAIN, PANEL_ELEMENT, PANEL_URL, STATIC_URL
from .data import PackingData

_DIR = Path(__file__).parent
_VERSION = json.loads((_DIR / "manifest.json").read_text())["version"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})

    data = PackingData(hass)
    await data.async_load()
    domain_data["data"] = data

    # Views and static paths cannot be unregistered, so register them only once.
    if not domain_data.get("registered"):
        for view in VIEWS:
            hass.http.register_view(view())
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(_DIR / "frontend"), cache_headers=False)]
        )
        domain_data["registered"] = True

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT,
        frontend_url_path=PANEL_URL,
        module_url=f"{STATIC_URL}/{PANEL_ELEMENT}.js?v={_VERSION}",
        sidebar_title="Pakkeliste",
        sidebar_icon="mdi:bag-suitcase",
        require_admin=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    frontend.async_remove_panel(hass, PANEL_URL)
    hass.data[DOMAIN].pop("data", None)
    return True
