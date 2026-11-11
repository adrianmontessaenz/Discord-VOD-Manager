"""HTTP client for Yggdrasil and the VodRepository built on top of it."""
import os
from typing import Any, List, Mapping, Optional

import requests

from .models import Vod
from .vod_repository import SqliteVodRepository, VodRepository


class YggdrasilError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, code: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.code = code


class YggdrasilUnavailable(YggdrasilError):
    """Connection error, timeout or 5xx: worth retrying later."""


class YggdrasilClient:
    def __init__(self, base_url: str, token: str, http: Optional[Any] = None, timeout: float = 15):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.http = http if http is not None else requests.Session()
        self.timeout = timeout
        self.per_page = 500

    # --- low level ---
    def _request(self, method: str, path: str, params: Optional[dict] = None,
                 json: Optional[dict] = None):
        try:
            res = self.http.request(
                method, f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                params=params, json=json, timeout=self.timeout)
        except requests.RequestException as e:
            raise YggdrasilUnavailable(f"Yggdrasil unreachable: {e}") from e
        if res.status_code >= 500:
            raise YggdrasilUnavailable(f"Yggdrasil error {res.status_code}", status=res.status_code,
                                       code=self._error_field(res, "code"))
        if res.status_code >= 400:
            raise YggdrasilError(self._error_field(res, "message") or f"HTTP {res.status_code}",
                                 status=res.status_code, code=self._error_field(res, "code"))
        return res

    @staticmethod
    def _error_field(res, field: str) -> Optional[str]:
        try:
            return res.json()["error"][field]
        except (ValueError, KeyError, TypeError):
            return None

    def _all_pages(self, path: str, params: Optional[dict] = None) -> List[dict]:
        items: List[dict] = []
        page = 1
        while True:
            body = self._request("GET", path, {**(params or {}), "page": page,
                                               "per_page": self.per_page}).json()
            items.extend(body["items"])
            if page * body["per_page"] >= body["total"] or not body["items"]:
                return items
            page += 1

    # --- sources ---
    def list_sources(self) -> List[dict]:
        return self._all_pages("/v1/sources/youtube")

    def add_source(self, channel: str, name: Optional[str] = None) -> dict:
        body = {"channel": channel}
        if name:
            body["name"] = name
        return self._request("POST", "/v1/sources/youtube", json=body).json()

    def remove_source(self, channel_id: str) -> bool:
        try:
            self._request("DELETE", f"/v1/sources/youtube/{channel_id}")
        except YggdrasilError as e:
            if e.status == 404:
                return False
            raise
        return True

    def request_history(self, channel_id: str) -> None:
        self._request("POST", f"/v1/ingest/youtube/{channel_id}/history")

    # --- vods ---
    def list_vods(self, since: Optional[int] = None) -> List[dict]:
        return self._all_pages("/v1/vods", {"since": since} if since is not None else None)

    def latest_revision(self) -> int:
        return int(self._request("GET", "/v1/vods", {"page": 1, "per_page": 1}).json()["revision"])

    def get_vod(self, video_id: str) -> Optional[dict]:
        try:
            return self._request("GET", f"/v1/vods/{video_id}").json()
        except YggdrasilError as e:
            if e.status == 404:
                return None
            raise


def vod_from_json(item: Mapping[str, Any]) -> Vod:
    return Vod(
        video_id=item["video_id"], title=item["title"], url=item["url"],
        published_at=str(item["published_at"]), youtube_channel_id=item.get("channel_id"),
        players=tuple(p["tag"] for p in item.get("players", [])),
        characters=tuple(item.get("characters", [])),
        tournament=item.get("tournament"), revision=int(item.get("revision", 0)))


class YggdrasilVodRepository:
    """VodRepository over the Yggdrasil API."""

    def __init__(self, client: YggdrasilClient):
        self.client = client

    def get(self, video_id: str) -> Optional[Vod]:
        item = self.client.get_vod(video_id)
        return vod_from_json(item) if item else None

    def list(self, youtube_channel_id: Optional[str] = None,
             since_revision: Optional[int] = None) -> List[Vod]:
        vods = [vod_from_json(i) for i in self.client.list_vods(since=since_revision)]
        if youtube_channel_id is not None:
            vods = [v for v in vods if v.youtube_channel_id == youtube_channel_id]
        return sorted(vods, key=lambda v: v.published_at)

    def latest_revision(self) -> int:
        return self.client.latest_revision()


def build_vod_repository(env: Mapping[str, str] = os.environ) -> VodRepository:
    url, token = env.get("YGGDRASIL_URL"), env.get("YGGDRASIL_TOKEN")
    if url and token:
        return YggdrasilVodRepository(YggdrasilClient(url, token))
    return SqliteVodRepository()
