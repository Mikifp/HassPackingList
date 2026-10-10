"""Pakkeliste: tiny JSON API plus static frontend, standard library only."""
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from seed import build_seed, uid

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_FILE = DATA_DIR / "packing.json"
WEB_DIR = Path(__file__).parent / "web"
PORT = int(os.environ.get("PORT", "8099"))

LOCK = threading.Lock()


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- storage ----------

def load():
    if DB_FILE.exists():
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    state = build_seed()
    save(state)
    return state


def save(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DB_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DB_FILE)


# ---------- helpers ----------

def text(value, field="name"):
    if not isinstance(value, str) or not value.strip():
        raise HttpError(400, f"{field} is required")
    return value.strip()[:200]


def qty(value):
    try:
        return max(1, min(999, int(value)))
    except (TypeError, ValueError):
        return 1


def find_trip(state, trip_id):
    for trip in state["trips"]:
        if trip["id"] == trip_id:
            return trip
    raise HttpError(404, "trip not found")


def find_item(trip, item_id):
    for item in trip["items"]:
        if item["id"] == item_id:
            return item
    raise HttpError(404, "item not found")


def clean_template(body):
    """Validate a template sent by the editor and assign ids where missing."""
    presets = [text(p, "preset") for p in body.get("presets", [])]
    presets = list(dict.fromkeys(presets))
    cats = []
    for c in body.get("template", []):
        items = []
        for i in c.get("items", []):
            items.append({
                "id": str(i.get("id") or uid()),
                "name": text(i.get("name")),
                "qty": qty(i.get("qty", 1)),
                "presets": [p for p in i.get("presets", []) if p in presets],
            })
        cats.append({"id": str(c.get("id") or uid()), "name": text(c.get("name")), "items": items})
    return presets, cats


def trip_summary(trip):
    return {
        "id": trip["id"], "name": trip["name"], "preset": trip.get("preset"),
        "created": trip["created"], "total": len(trip["items"]),
        "packed": sum(1 for i in trip["items"] if i["packed"]),
    }


# ---------- API handlers ----------

def create_trip(state, body):
    name = text(body.get("name"))
    preset = body.get("preset") or None
    if preset and preset not in state["presets"]:
        raise HttpError(400, "unknown preset")
    cats, items = [], []
    for c in state["template"]:
        picked = [i for i in c["items"] if not preset or preset in i["presets"]]
        if not picked:
            continue
        cats.append(c["name"])
        for i in picked:
            items.append({"id": uid(), "cat": c["name"], "name": i["name"], "qty": i["qty"], "packed": False})
    trip = {
        "id": uid(), "name": name, "preset": preset,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cats": cats, "items": items,
    }
    state["trips"].append(trip)
    return trip


def add_item(trip, body):
    cat = text(body.get("cat"), "cat")
    if cat not in trip["cats"]:
        trip["cats"].append(cat)
    item = {"id": uid(), "cat": cat, "name": text(body.get("name")), "qty": qty(body.get("qty", 1)), "packed": False}
    trip["items"].append(item)
    return item


def patch_item(item, body):
    if "packed" in body:
        item["packed"] = bool(body["packed"])
    if "qty" in body:
        item["qty"] = qty(body["qty"])
    if "name" in body:
        item["name"] = text(body["name"])


def delete_item(trip, item_id):
    item = find_item(trip, item_id)
    trip["items"].remove(item)
    # Drop categories that have become empty, but only when their last item goes.
    if not any(i["cat"] == item["cat"] for i in trip["items"]):
        trip["cats"].remove(item["cat"])


ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile(f"^{pattern}$"), fn))
        return fn
    return deco


@route("GET", "/api/state")
def r_state(state, body):
    return {
        "presets": state["presets"], "template": state["template"],
        "trips": [trip_summary(t) for t in state["trips"]],
    }, False


@route("PUT", "/api/template")
def r_put_template(state, body):
    state["presets"], state["template"] = clean_template(body)
    return {"ok": True}, True


@route("POST", "/api/trips")
def r_create_trip(state, body):
    return create_trip(state, body), True


@route("GET", "/api/trips/(?P<tid>[^/]+)")
def r_get_trip(state, body, tid):
    return find_trip(state, tid), False


@route("PATCH", "/api/trips/(?P<tid>[^/]+)")
def r_patch_trip(state, body, tid):
    trip = find_trip(state, tid)
    if "name" in body:
        trip["name"] = text(body["name"])
    if "add_cat" in body:
        cat = text(body["add_cat"], "add_cat")
        if cat not in trip["cats"]:
            trip["cats"].append(cat)
    if body.get("reset"):
        for i in trip["items"]:
            i["packed"] = False
    return trip, True


@route("DELETE", "/api/trips/(?P<tid>[^/]+)")
def r_delete_trip(state, body, tid):
    state["trips"].remove(find_trip(state, tid))
    return {"ok": True}, True


@route("POST", "/api/trips/(?P<tid>[^/]+)/items")
def r_add_item(state, body, tid):
    return add_item(find_trip(state, tid), body), True


@route("PATCH", "/api/trips/(?P<tid>[^/]+)/items/(?P<iid>[^/]+)")
def r_patch_item(state, body, tid, iid):
    item = find_item(find_trip(state, tid), iid)
    patch_item(item, body)
    return item, True


@route("DELETE", "/api/trips/(?P<tid>[^/]+)/items/(?P<iid>[^/]+)")
def r_delete_item(state, body, tid, iid):
    delete_item(find_trip(state, tid), iid)
    return {"ok": True}, True


# ---------- HTTP plumbing ----------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_bytes(self, status, payload, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status, obj):
        self.send_bytes(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def handle_any(self, method):
        path = urlparse(self.path).path
        if method == "GET" and path in ("/", "/index.html"):
            return self.send_bytes(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise HttpError(400, "JSON object expected")
            for m, pattern, fn in ROUTES:
                match = pattern.match(path)
                if m == method and match:
                    with LOCK:
                        state = load()
                        result, changed = fn(state, body, **match.groupdict())
                        if changed:
                            save(state)
                    return self.send_json(200, result)
            raise HttpError(404, "not found")
        except HttpError as e:
            self.send_json(e.status, {"error": e.message})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid JSON"})

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")

    def do_PUT(self):
        self.handle_any("PUT")

    def do_PATCH(self):
        self.handle_any("PATCH")

    def do_DELETE(self):
        self.handle_any("DELETE")


if __name__ == "__main__":
    with LOCK:
        load()  # seeds the template on first start
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
