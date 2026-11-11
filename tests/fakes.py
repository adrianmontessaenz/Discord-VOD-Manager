"""In-memory stand-in for the Yggdrasil HTTP API (the `requests.Session` surface the client uses)."""
import math
from urllib.parse import urlparse

import requests


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


def error(status, code, message):
    return FakeResponse(status, {"error": {"code": code, "message": message}})


class FakeYggdrasil:
    def __init__(self, token="secret"):
        self.token = token
        self.sources = {}          # channel_id -> dict
        self.vods = []             # list of API-shaped dicts (with "revision")
        self.history_requests = []
        self.requests = []         # (method, path, params)
        self.down = False          # raise ConnectionError
        self.fail_status = None    # force this status on every call
        self._revision = 0

    # --- helpers to load data ---
    def add_vod(self, video_id, channel_id, published_at, title="t", players=(), characters=(),
                tournament=None, revision=None):
        self._revision = max(self._revision, revision) if revision else self._revision + 1
        rev = revision or self._revision
        self.vods = [v for v in self.vods if v["video_id"] != video_id]
        self.vods.append({
            "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title, "channel_id": channel_id, "channel_name": None,
            "published_at": published_at, "tournament": tournament,
            "players": [{"tag": p, "user_id": None} for p in players],
            "characters": list(characters), "sets": [], "revision": rev})
        return rev

    # --- requests.Session surface ---
    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        path = urlparse(url).path
        self.requests.append((method, path, dict(params or {}), dict(headers or {})))
        if self.down:
            raise requests.ConnectionError("down")
        if self.fail_status:
            return error(self.fail_status, "boom", "forced")
        if (headers or {}).get("Authorization") != f"Bearer {self.token}":
            return error(401, "unauthorized", "bad token")
        params = params or {}
        if method == "GET" and path == "/v1/sources/youtube":
            return self._page(sorted(self.sources.values(), key=lambda s: s["name"]), params, None)
        if method == "POST" and path == "/v1/sources/youtube":
            ref = json["channel"]
            if not (ref.startswith("UC") or ref.startswith("@")):
                return error(422, "validation_error", "channel must be a channel id (UC...) or a @handle")
            cid = ref if ref.startswith("UC") else "UC" + ref[1:]
            name = json.get("name") or (ref[1:] if ref.startswith("@") else cid)
            created = cid not in self.sources
            self.sources.setdefault(cid, {"channel_id": cid, "name": name})
            return FakeResponse(201 if created else 200, self.sources[cid])
        if method == "DELETE" and path.startswith("/v1/sources/youtube/"):
            cid = path.rsplit("/", 1)[1]
            if cid not in self.sources:
                return error(404, "not_found", f"YouTube channel {cid} is not registered")
            del self.sources[cid]
            return FakeResponse(204)
        if method == "POST" and path.startswith("/v1/ingest/youtube/") and path.endswith("/history"):
            cid = path.split("/")[4]
            if cid not in self.sources:
                return error(404, "not_found", f"YouTube channel {cid} is not registered")
            self.history_requests.append(cid)
            return FakeResponse(202, {"job_id": 1})
        if method == "GET" and path == "/v1/vods":
            since = int(params["since"]) if "since" in params else None
            items = sorted(self.vods, key=lambda v: v["revision"])
            if since is not None:
                items = [v for v in items if v["revision"] > since]
            return self._page(items, params, "revision", since)
        if method == "GET" and path.startswith("/v1/vods/"):
            vid = path.rsplit("/", 1)[1]
            for v in self.vods:
                if v["video_id"] == vid:
                    return FakeResponse(200, v)
            return error(404, "not_found", f"VOD {vid} not found")
        return error(404, "not_found", path)

    def _page(self, items, params, revision_key, since=None):
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 100))
        chunk = items[(page - 1) * per_page: page * per_page]
        revision = max((i[revision_key] for i in items), default=since or 0) if revision_key else 0
        return FakeResponse(200, {"items": chunk, "page": page, "per_page": per_page,
                                  "total": len(items), "revision": revision,
                                  "pages": max(1, math.ceil(len(items) / per_page))})
