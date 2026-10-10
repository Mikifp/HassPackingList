"""HTTP API used by the panel. All endpoints require Home Assistant authentication."""
from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .data import PackingData, PackingError

BASE = "/api/packing_list"


async def _body(request: web.Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


class _View(HomeAssistantView):
    requires_auth = True

    def _data(self, request: web.Request) -> PackingData:
        try:
            return request.app["hass"].data[DOMAIN]["data"]
        except KeyError:
            raise PackingError(503, "Pakkeliste is not loaded") from None

    async def _run(self, request, fn):
        try:
            return self.json(fn(self._data(request), await _body(request)))
        except PackingError as err:
            return self.json_message(err.message, err.status)


class StateView(_View):
    url = f"{BASE}/state"
    name = "api:packing_list:state"

    async def get(self, request):
        return await self._run(request, lambda d, b: d.overview())


class TemplateView(_View):
    url = f"{BASE}/template"
    name = "api:packing_list:template"

    async def put(self, request):
        return await self._run(request, lambda d, b: d.set_template(b))


class TripsView(_View):
    url = f"{BASE}/trips"
    name = "api:packing_list:trips"

    async def post(self, request):
        return await self._run(request, lambda d, b: d.create_trip(b))


class TripView(_View):
    url = f"{BASE}/trips/{{trip_id}}"
    name = "api:packing_list:trip"

    async def get(self, request, trip_id):
        return await self._run(request, lambda d, b: d.get_trip(trip_id))

    async def patch(self, request, trip_id):
        return await self._run(request, lambda d, b: d.patch_trip(trip_id, b))

    async def delete(self, request, trip_id):
        return await self._run(request, lambda d, b: d.delete_trip(trip_id))


class TripItemsView(_View):
    url = f"{BASE}/trips/{{trip_id}}/items"
    name = "api:packing_list:items"

    async def post(self, request, trip_id):
        return await self._run(request, lambda d, b: d.add_item(trip_id, b))


class TripItemView(_View):
    url = f"{BASE}/trips/{{trip_id}}/items/{{item_id}}"
    name = "api:packing_list:item"

    async def patch(self, request, trip_id, item_id):
        return await self._run(request, lambda d, b: d.patch_item(trip_id, item_id, b))

    async def delete(self, request, trip_id, item_id):
        return await self._run(request, lambda d, b: d.delete_item(trip_id, item_id))


VIEWS = (StateView, TemplateView, TripsView, TripView, TripItemsView, TripItemView)
