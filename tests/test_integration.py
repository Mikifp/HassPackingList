from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.packing_list.const import DOMAIN, PANEL_URL


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_panel_registered_and_seeded(hass, hass_client):
    await _setup(hass)
    assert PANEL_URL in hass.data["frontend_panels"]
    client = await hass_client()
    state = await (await client.get("/api/packing_list/state")).json()
    assert state["presets"] == ["Sommerhus", "Badeferie", "Sommerlejr"]
    assert len(state["template"]) == 9
    shorts = [i for c in state["template"] for i in c["items"] if i["name"] == "Shorts"][0]
    assert shorts["qty"] == 7


async def test_trip_workflow(hass, hass_client):
    await _setup(hass)
    client = await hass_client()

    resp = await client.post("/api/packing_list/trips", json={"name": "Ferie", "preset": "Badeferie"})
    trip = await resp.json()
    cats = set(trip["cats"])
    assert "Håndbagage" in cats and "Spil" not in cats  # Spil is not a Badeferie category

    item = trip["items"][0]
    url = f"/api/packing_list/trips/{trip['id']}/items/{item['id']}"
    assert (await (await client.patch(url, json={"packed": True, "qty": 3})).json())["packed"] is True

    added = await (await client.post(f"/api/packing_list/trips/{trip['id']}/items", json={"cat": "Ekstra", "name": "Kaffe", "qty": 2})).json()
    assert added["cat"] == "Ekstra"

    summary = (await (await client.get("/api/packing_list/state")).json())["trips"][0]
    assert summary["packed"] == 1 and summary["total"] == len(trip["items"]) + 1

    await client.delete(f"/api/packing_list/trips/{trip['id']}/items/{added['id']}")
    full = await (await client.get(f"/api/packing_list/trips/{trip['id']}")).json()
    assert "Ekstra" not in full["cats"]

    assert (await client.get("/api/packing_list/trips/nope")).status == 404
    assert (await client.post("/api/packing_list/trips", json={"name": ""})).status == 400
    assert (await client.delete(f"/api/packing_list/trips/{trip['id']}")).status == 200


async def test_template_edit_and_unload(hass, hass_client):
    entry = await _setup(hass)
    client = await hass_client()
    state = await (await client.get("/api/packing_list/state")).json()
    state["template"] = state["template"][:1]
    assert (await client.put("/api/packing_list/template", json=state)).status == 200
    assert len((await (await client.get("/api/packing_list/state")).json())["template"]) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL not in hass.data["frontend_panels"]
    # Reload re-registers without error (views/static paths are only registered once).
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert PANEL_URL in hass.data["frontend_panels"]
