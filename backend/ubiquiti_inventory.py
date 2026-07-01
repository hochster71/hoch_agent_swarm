from __future__ import annotations

import json
import os
import ssl
import urllib.request
import urllib.error
import http.cookiejar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


OUT_PATH = Path("artifacts/qa/ubiquiti/latest_ubiquiti_inventory.json")

DEFAULT_AI_PORTS = [11434, 1234, 8080, 8000, 5000, 5001, 3000, 5173, 7860, 8188, 8888]


def now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "y"}


class UniFiLocalClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("UNIFI_BASE_URL", "https://10.0.0.1").rstrip("/")
        self.username = os.getenv("UNIFI_USERNAME", "")
        self.password = os.getenv("UNIFI_PASSWORD", "")
        self.site = os.getenv("UNIFI_SITE", "default")
        verify_ssl = env_bool("UNIFI_VERIFY_SSL", False)

        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.ctx = None if verify_ssl else ssl._create_unverified_context()

    def request(self, method: str, path: str, payload: Optional[dict] = None, timeout: int = 20) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "hoch-agent-swarm-local-discovery/1.0",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with self.opener.open(req, timeout=timeout, context=self.ctx) as res:
            raw = res.read(20_000_000)
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8", "ignore"))

    def login(self) -> Dict[str, Any]:
        if not self.username or not self.password:
            return {
                "ok": False,
                "reason": "UNIFI_USERNAME / UNIFI_PASSWORD not set",
            }

        attempts = [
            ("/api/auth/login", {"username": self.username, "password": self.password}),
            ("/api/login", {"username": self.username, "password": self.password}),
        ]

        errors = []
        for path, payload in attempts:
            try:
                data = self.request("POST", path, payload)
                return {"ok": True, "path": path, "response_type": type(data).__name__}
            except Exception as exc:
                errors.append({"path": path, "error": str(exc)})

        return {"ok": False, "reason": "login failed", "errors": errors}

    def get_first(self, paths: List[str]) -> Dict[str, Any]:
        errors = []
        for path in paths:
            try:
                data = self.request("GET", path)
                return {"ok": True, "path": path, "data": data}
            except Exception as exc:
                errors.append({"path": path, "error": str(exc)})
        return {"ok": False, "errors": errors}

    def collect(self) -> Dict[str, Any]:
        login = self.login()

        site = self.site
        collections = {
            "active_clients": [
                f"/proxy/network/api/s/{site}/stat/sta",
                f"/api/s/{site}/stat/sta",
            ],
            "known_clients": [
                f"/proxy/network/api/s/{site}/rest/user",
                f"/api/s/{site}/rest/user",
            ],
            "network_devices": [
                f"/proxy/network/api/s/{site}/stat/device",
                f"/api/s/{site}/stat/device",
            ],
            "health": [
                f"/proxy/network/api/s/{site}/stat/health",
                f"/api/s/{site}/stat/health",
            ],
            "sysinfo": [
                f"/proxy/network/api/s/{site}/stat/sysinfo",
                f"/api/s/{site}/stat/sysinfo",
                "/proxy/network/api/status",
                "/api/status",
            ],
            "self": [
                "/proxy/network/api/self",
                "/api/self",
            ],
        }

        results = {}
        for name, paths in collections.items():
            if login.get("ok"):
                results[name] = self.get_first(paths)
            else:
                results[name] = {"ok": False, "reason": "login not established"}

        return {
            "login": login,
            "base_url": self.base_url,
            "site": site,
            "collections": results,
        }


def unwrap_rows(collection: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not collection.get("ok"):
        return []
    data = collection.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return [x for x in data["data"] if isinstance(x, dict)]
        if isinstance(data.get("items"), list):
            return [x for x in data["items"] if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def normalize_client(row: Dict[str, Any], source: str) -> Dict[str, Any]:
    ip = row.get("ip") or row.get("fixed_ip") or row.get("last_ip") or row.get("hostname")
    mac = row.get("mac") or row.get("_id")
    name = (
        row.get("name")
        or row.get("hostname")
        or row.get("display_name")
        or row.get("oui")
        or row.get("dev_cat_name")
        or mac
        or ip
    )
    ssid = row.get("essid") or row.get("network") or row.get("wireless_network")
    return {
        "id": mac or ip or name,
        "ip": ip,
        "mac": mac,
        "name": name,
        "hostname": row.get("hostname"),
        "alias": row.get("name"),
        "ssid": ssid,
        "is_wired": row.get("is_wired"),
        "ap_mac": row.get("ap_mac"),
        "uptime": row.get("uptime"),
        "last_seen": row.get("last_seen"),
        "signal": row.get("signal"),
        "rx_bytes": row.get("rx_bytes"),
        "tx_bytes": row.get("tx_bytes"),
        "source": source,
        "raw_keys": sorted(row.keys()),
    }


def merge_inventory(raw: Dict[str, Any]) -> Dict[str, Any]:
    collections = raw.get("collections", {})

    active = [normalize_client(r, "unifi_active_clients") for r in unwrap_rows(collections.get("active_clients", {}))]
    known = [normalize_client(r, "unifi_known_clients") for r in unwrap_rows(collections.get("known_clients", {}))]
    devices = [normalize_client(r, "unifi_network_devices") for r in unwrap_rows(collections.get("network_devices", {}))]

    by_key: Dict[str, Dict[str, Any]] = {}
    for row in known + active + devices:
        key = row.get("mac") or row.get("ip") or row.get("name")
        if not key:
            continue
        existing = by_key.get(key, {})
        merged = {**existing, **{k: v for k, v in row.items() if v not in [None, "", []]}}
        sources = set(existing.get("sources", []))
        sources.add(row["source"])
        merged["sources"] = sorted(sources)
        by_key[key] = merged

    clients = list(by_key.values())

    billie = [
        c for c in clients
        if str(c.get("ssid") or "").lower() == "billie"
        or "billie" in str(c.get("ssid") or "").lower()
    ]

    return {
        "total_clients": len(clients),
        "billie_clients": len(billie),
        "active_clients": len(active),
        "known_clients": len(known),
        "network_devices": len(devices),
        "clients": clients,
        "billie": billie,
        "health": collections.get("health"),
        "sysinfo": collections.get("sysinfo"),
    }


def collect_ubiquiti_inventory() -> Dict[str, Any]:
    raw = UniFiLocalClient().collect()
    merged = merge_inventory(raw)

    payload = {
        "schema": "hoch.ubiquiti_inventory.v1",
        "generated_at": now_z(),
        "truth": "LIVE" if raw.get("login", {}).get("ok") else "AUTH_REQUIRED",
        "raw_login": raw.get("login"),
        "base_url": raw.get("base_url"),
        "site": raw.get("site"),
        "summary": {
            "total_clients": merged["total_clients"],
            "billie_clients": merged["billie_clients"],
            "active_clients": merged["active_clients"],
            "known_clients": merged["known_clients"],
            "network_devices": merged["network_devices"],
        },
        "clients": merged["clients"],
        "billie": merged["billie"],
        "health": merged["health"],
        "sysinfo": merged["sysinfo"],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
