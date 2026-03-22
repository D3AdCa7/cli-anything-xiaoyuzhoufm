"""HTTP client for XiaoYuZhou FM API.

Uses a dual-channel strategy:
- Public data (episodes, podcasts, search): Next.js SSR data endpoints (no auth needed)
- Authenticated actions (subscriptions, transcript, history): Mobile API with tokens
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.xiaoyuzhoufm.com"
WEB_BASE = "https://www.xiaoyuzhoufm.com"

# Build ID for Next.js data endpoints — updated periodically
_BUILD_ID_CACHE: str | None = None

MOBILE_HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "App-BuildNo": "1576",
    "OS": "ios",
    "Manufacturer": "Apple",
    "BundleID": "app.podcast.cosmos",
}

WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _config_dir() -> Path:
    override = os.environ.get("CLI_ANYTHING_XIAOYUZHOUFM_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "cli-anything-xiaoyuzhoufm"


def _auth_path() -> Path:
    return _config_dir() / "auth.json"


def load_auth() -> dict:
    path = _auth_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_auth(data: dict) -> None:
    path = _auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def clear_auth() -> None:
    path = _auth_path()
    if path.exists():
        path.unlink()


def get_device_id() -> str:
    auth = load_auth()
    if "device_id" in auth:
        return auth["device_id"]
    device_id = str(uuid.uuid4()).upper()
    auth["device_id"] = device_id
    save_auth(auth)
    return device_id


def _fetch_build_id() -> str:
    """Fetch current Next.js build ID from the homepage."""
    global _BUILD_ID_CACHE
    if _BUILD_ID_CACHE:
        return _BUILD_ID_CACHE
    # Check cached build ID
    auth = load_auth()
    cached = auth.get("build_id")
    if cached:
        _BUILD_ID_CACHE = cached
        return cached
    # Fetch from homepage
    resp = requests.get(WEB_BASE, headers=WEB_HEADERS, timeout=10)
    match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
    if match:
        _BUILD_ID_CACHE = match.group(1)
        auth["build_id"] = _BUILD_ID_CACHE
        save_auth(auth)
        return _BUILD_ID_CACHE
    raise RuntimeError("Cannot determine Next.js build ID. Website may have changed.")


def _invalidate_build_id() -> None:
    """Clear cached build ID so next call fetches fresh."""
    global _BUILD_ID_CACHE
    _BUILD_ID_CACHE = None
    auth = load_auth()
    auth.pop("build_id", None)
    save_auth(auth)


class XYZClient:
    """HTTP client for xiaoyuzhoufm.com.

    Public data is fetched through Next.js SSR endpoints (no auth).
    Authenticated operations use the mobile API.
    """

    def __init__(self) -> None:
        self.web_session = requests.Session()
        self.web_session.headers.update(WEB_HEADERS)

        self.api_session = requests.Session()
        self.api_session.headers.update(MOBILE_HEADERS)

        auth = load_auth()
        self._access_token: str | None = auth.get("access_token")
        self._refresh_token: str | None = auth.get("refresh_token")
        self._device_id: str = get_device_id()
        self.api_session.headers["x-jike-device-id"] = self._device_id

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    def _set_auth_header(self) -> None:
        if self._access_token:
            self.api_session.headers["x-jike-access-token"] = self._access_token
        else:
            self.api_session.headers.pop("x-jike-access-token", None)

    def _save_tokens(self, access: str, refresh: str) -> None:
        self._access_token = access
        self._refresh_token = refresh
        auth = load_auth()
        auth["access_token"] = access
        auth["refresh_token"] = refresh
        save_auth(auth)
        self._set_auth_header()

    def refresh_token(self) -> bool:
        if not self._refresh_token:
            return False
        headers = {
            "x-jike-access-token": self._access_token or "",
            "x-jike-refresh-token": self._refresh_token,
        }
        resp = self.api_session.post(
            f"{API_BASE}/app_auth_tokens.refresh",
            headers=headers,
        )
        if resp.status_code == 200:
            new_access = resp.headers.get("x-jike-access-token", "")
            new_refresh = resp.headers.get("x-jike-refresh-token", "")
            if new_access and new_refresh:
                self._save_tokens(new_access, new_refresh)
                return True
        return False

    # ── Web (Next.js) endpoints ──────────────────────────────────────

    def _web_get(self, page_type: str, resource_id: str) -> dict:
        """Fetch data from Next.js SSR endpoint. No auth required."""
        build_id = _fetch_build_id()
        url = f"{WEB_BASE}/_next/data/{build_id}/{page_type}/{resource_id}.json"
        resp = self.web_session.get(url, params={"id": resource_id}, timeout=15)

        # Build ID may be stale
        if resp.status_code == 404:
            _invalidate_build_id()
            build_id = _fetch_build_id()
            url = f"{WEB_BASE}/_next/data/{build_id}/{page_type}/{resource_id}.json"
            resp = self.web_session.get(url, params={"id": resource_id}, timeout=15)

        if resp.status_code >= 400:
            raise RuntimeError(f"Web API error {resp.status_code} for {page_type}/{resource_id}")

        return resp.json().get("pageProps", {})

    # ── Mobile API endpoints ─────────────────────────────────────────

    def _api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        auth_required: bool = False,
    ) -> dict:
        if auth_required and not self.is_authenticated:
            raise RuntimeError("Authentication required. Run: cli-anything-xiaoyuzhoufm auth login")

        self._set_auth_header()
        url = f"{API_BASE}{path}"
        resp = self.api_session.request(method, url, params=params, json=json_body)

        if resp.status_code == 401 and self._refresh_token:
            if self.refresh_token():
                resp = self.api_session.request(method, url, params=params, json=json_body)

        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = {"status": resp.status_code, "body": resp.text[:500]}
            raise RuntimeError(f"API error {resp.status_code}: {json.dumps(err, ensure_ascii=False)}")

        return resp.json()

    def _api_get(self, path: str, *, params: dict | None = None, auth_required: bool = False) -> dict:
        return self._api_request("GET", path, params=params, auth_required=auth_required)

    def _api_post(self, path: str, *, json_body: dict | None = None, auth_required: bool = False) -> dict:
        return self._api_request("POST", path, json_body=json_body or {}, auth_required=auth_required)

    # ── Auth ──────────────────────────────────────────────────────────

    def send_code(self, phone: str, area_code: str = "+86") -> dict:
        return self._api_post("/v1/auth/sendCode", json_body={
            "mobilePhoneNumber": phone,
            "areaCode": area_code,
        })

    def login_with_sms(self, phone: str, code: str, area_code: str = "+86") -> dict:
        resp = self.api_session.post(
            f"{API_BASE}/v1/auth/loginOrSignUpWithSMS",
            json={"mobilePhoneNumber": phone, "verifyCode": code, "areaCode": area_code},
        )
        if resp.status_code == 200:
            access = resp.headers.get("x-jike-access-token", "")
            refresh = resp.headers.get("x-jike-refresh-token", "")
            if access and refresh:
                self._save_tokens(access, refresh)
            return resp.json()
        try:
            err = resp.json()
        except Exception:
            err = {"status": resp.status_code}
        raise RuntimeError(f"Login failed: {json.dumps(err, ensure_ascii=False)}")

    # ── Podcast (web — no auth) ───────────────────────────────────────

    def podcast_get(self, pid: str) -> dict:
        """Get podcast info. Returns {podcast: {...}, episodes: [...]}."""
        data = self._web_get("podcast", pid)
        return {"data": data.get("podcast", data)}

    def podcast_episodes(self, pid: str, order: str = "desc", limit: int = 20, load_more_key: dict | None = None) -> dict:
        """List episodes. Uses web data for first page, API for pagination."""
        if not load_more_key:
            data = self._web_get("podcast", pid)
            podcast = data.get("podcast", {})
            episodes = podcast.get("episodes", [])
            if order == "asc":
                episodes = list(reversed(episodes))
            return {"data": episodes[:limit]}
        return self._api_post("/v1/episode/list", json_body={
            "pid": pid, "order": order, "limit": limit, "loadMoreKey": load_more_key,
        }, auth_required=True)

    def podcast_popular(self, pid: str) -> dict:
        return self._api_post("/v1/episode/list-by-filter", json_body={"pid": pid, "label": "POPULAR"}, auth_required=True)

    # ── Episode (web — no auth) ───────────────────────────────────────

    def episode_get(self, eid: str) -> dict:
        """Get episode details including audio URL."""
        data = self._web_get("episode", eid)
        return {"data": data.get("episode", data)}

    def episode_transcript(self, eid: str, media_id: str) -> dict:
        return self._api_post("/v1/episode-transcript/get", json_body={"eid": eid, "mediaId": media_id}, auth_required=True)

    # ── Comments (try web first, fallback to API) ─────────────────────

    def comment_list(self, eid: str, order: str = "hot", load_more_key: dict | None = None) -> dict:
        """List comments. Uses web data when available."""
        # Web episode pages include comments
        if not load_more_key:
            data = self._web_get("episode", eid)
            comments = data.get("comments", [])
            if comments:
                return {"data": comments}
        # Fallback to API (needs auth for pagination)
        body: dict[str, Any] = {"eid": eid, "order": order}
        if load_more_key:
            body["loadMoreKey"] = load_more_key
        return self._api_post("/v1/comment/list-primary", json_body=body, auth_required=True)

    # ── Search (web — scrape approach) ────────────────────────────────

    def search(self, keyword: str, result_type: str = "ALL", limit: int = 20, load_more_key: dict | None = None) -> dict:
        """Search. Requires auth via mobile API."""
        body: dict[str, Any] = {"keyword": keyword, "type": result_type, "limit": str(limit)}
        if load_more_key:
            body["loadMoreKey"] = load_more_key
        return self._api_post("/v1/search/create", json_body=body, auth_required=True)

    # ── Subscription (auth required) ──────────────────────────────────

    def subscription_list(self, limit: int = 50, load_more_key: dict | None = None) -> dict:
        body: dict[str, Any] = {"limit": limit, "sortOrder": "desc", "sortBy": "subscribedAt"}
        if load_more_key:
            body["loadMoreKey"] = load_more_key
        return self._api_post("/v1/subscription/list", json_body=body, auth_required=True)

    def subscription_update(self, pid: str, mode: str = "ON") -> dict:
        return self._api_post("/v1/subscription/update", json_body={"pid": pid, "mode": mode}, auth_required=True)

    # ── User (auth required) ─────────────────────────────────────────

    def profile_get(self, uid: str | None = None) -> dict:
        if uid:
            # Public profiles via web
            data = self._web_get("user", uid)
            return {"data": data.get("user", data)}
        return self._api_get("/v1/profile/get", auth_required=True)

    def user_stats(self, uid: str) -> dict:
        return self._api_get("/v1/user-stats/get", params={"uid": uid})

    def play_history(self, load_more_key: dict | None = None) -> dict:
        body: dict[str, Any] = {}
        if load_more_key:
            body["loadMoreKey"] = load_more_key
        return self._api_post("/v1/episode-played/list-history", json_body=body, auth_required=True)

    # ── Favorites (auth required) ─────────────────────────────────────

    def favorite_list(self) -> dict:
        return self._api_post("/v1/favorite/list", json_body={}, auth_required=True)

    def favorite_update(self, eid: str, favorited: bool = True) -> dict:
        return self._api_post("/v1/favorite/update", json_body={"eid": eid, "favorited": favorited}, auth_required=True)

    # ── Discovery (auth required for API) ─────────────────────────────

    def top_list(self, category: str = "HOT_EPISODES_IN_24_HOURS") -> dict:
        return self._api_get("/v1/top-list/get", params={"category": category}, auth_required=True)

    def category_list(self) -> dict:
        return self._api_post("/v1/category/list-all", json_body={}, auth_required=True)
