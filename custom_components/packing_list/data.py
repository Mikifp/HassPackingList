"""Packing list data model and persistence (no Home Assistant specifics except Store)."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .seed import build_seed, uid


class PackingError(Exception):
    """A request the API should answer with a 4xx status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _text(value, field="name"):
    if not isinstance(value, str) or not value.strip():
        raise PackingError(400, f"{field} is required")
    return value.strip()[:200]


def _qty(value):
    try:
        return max(1, min(999, int(value)))
    except (TypeError, ValueError):
        return 1


class PackingData:
    """Template + trips. Methods are synchronous on the in-memory state; the
    async wrappers persist afterwards. HA runs on one event loop, so there is
    no interleaving between the mutation and the scheduled save."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.state: dict = {}

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored is None:
            stored = build_seed()
            await self._store.async_save(stored)
        self.state = stored

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.state, 0.5)

    # ----- lookups -----
    def _trip(self, trip_id):
        for trip in self.state["trips"]:
            if trip["id"] == trip_id:
                return trip
        raise PackingError(404, "trip not found")

    @staticmethod
    def _item(trip, item_id):
        for item in trip["items"]:
            if item["id"] == item_id:
                return item
        raise PackingError(404, "item not found")

    # ----- overview / template -----
    def overview(self):
        return {
            "presets": self.state["presets"],
            "template": self.state["template"],
            "trips": [
                {
                    "id": t["id"], "name": t["name"], "preset": t.get("preset"),
                    "created": t["created"], "total": len(t["items"]),
                    "packed": sum(1 for i in t["items"] if i["packed"]),
                }
                for t in self.state["trips"]
            ],
        }

    def set_template(self, body):
        presets = list(dict.fromkeys(_text(p, "preset") for p in body.get("presets", [])))
        cats = []
        for c in body.get("template", []):
            items = [
                {
                    "id": str(i.get("id") or uid()),
                    "name": _text(i.get("name")),
                    "qty": _qty(i.get("qty", 1)),
                    "presets": [p for p in i.get("presets", []) if p in presets],
                }
                for i in c.get("items", [])
            ]
            cats.append({"id": str(c.get("id") or uid()), "name": _text(c.get("name")), "items": items})
        self.state["presets"], self.state["template"] = presets, cats
        self._save()
        return {"ok": True}

    # ----- trips -----
    def create_trip(self, body):
        name = _text(body.get("name"))
        preset = body.get("preset") or None
        if preset and preset not in self.state["presets"]:
            raise PackingError(400, "unknown preset")
        cats, items = [], []
        for c in self.state["template"]:
            picked = [i for i in c["items"] if not preset or preset in i["presets"]]
            if not picked:
                continue
            cats.append(c["name"])
            items += [
                {"id": uid(), "cat": c["name"], "name": i["name"], "qty": i["qty"], "packed": False}
                for i in picked
            ]
        trip = {
            "id": uid(), "name": name, "preset": preset,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cats": cats, "items": items,
        }
        self.state["trips"].append(trip)
        self._save()
        return trip

    def get_trip(self, trip_id):
        return self._trip(trip_id)

    def patch_trip(self, trip_id, body):
        trip = self._trip(trip_id)
        if "name" in body:
            trip["name"] = _text(body["name"])
        if "add_cat" in body:
            cat = _text(body["add_cat"], "add_cat")
            if cat not in trip["cats"]:
                trip["cats"].append(cat)
        if body.get("reset"):
            for i in trip["items"]:
                i["packed"] = False
        self._save()
        return trip

    def delete_trip(self, trip_id):
        self.state["trips"].remove(self._trip(trip_id))
        self._save()
        return {"ok": True}

    # ----- trip items -----
    def add_item(self, trip_id, body):
        trip = self._trip(trip_id)
        cat = _text(body.get("cat"), "cat")
        if cat not in trip["cats"]:
            trip["cats"].append(cat)
        item = {"id": uid(), "cat": cat, "name": _text(body.get("name")), "qty": _qty(body.get("qty", 1)), "packed": False}
        trip["items"].append(item)
        self._save()
        return item

    def patch_item(self, trip_id, item_id, body):
        item = self._item(self._trip(trip_id), item_id)
        if "packed" in body:
            item["packed"] = bool(body["packed"])
        if "qty" in body:
            item["qty"] = _qty(body["qty"])
        if "name" in body:
            item["name"] = _text(body["name"])
        self._save()
        return item

    def delete_item(self, trip_id, item_id):
        trip = self._trip(trip_id)
        item = self._item(trip, item_id)
        trip["items"].remove(item)
        # A category disappears from the trip when its last item is removed.
        if not any(i["cat"] == item["cat"] for i in trip["items"]):
            trip["cats"].remove(item["cat"])
        self._save()
        return {"ok": True}
