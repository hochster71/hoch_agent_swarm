import os
import re
import time
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Cache storage
_PLAYLIST_CACHE = {
    "data": None,
    "raw_m3u": "",
    "loaded_at": 0,
    "error": None
}

_EPG_CACHE = {
    "raw_xml": "",
    "loaded_at": 0,
    "error": None
}

def get_tv_config() -> dict:
    return {
        "playlist_url": os.getenv("DROGON_PLAYLIST_URL", "https://drogon.tv/w/yNVuoC49uwRDepuKoF"),
        "epg_url": os.getenv("DROGON_EPG_URL", "https://drogon.tv/g/yNVuoC49uwRDepuKoF"),
        "playlist_ttl": int(os.getenv("TV_CACHE_PLAYLIST_SECONDS", "900")),
        "epg_ttl": int(os.getenv("TV_CACHE_EPG_SECONDS", "3600"))
    }

def redact_url(url: str) -> str:
    """Redacts tokens, credentials, or query parameters in logs and diagnostics."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # Redact password in netloc
        netloc = parsed.netloc
        if "@" in netloc:
            parts = netloc.split("@")
            userpass = parts[0]
            host = parts[1]
            if ":" in userpass:
                u, p = userpass.split(":", 1)
                netloc = f"{u}:[REDACTED]@{host}"
            else:
                netloc = f"[REDACTED]@{host}"
        
        # Redact query params
        if parsed.query:
            params = parse_qsl(parsed.query)
            redacted_params = []
            for k, v in params:
                if any(x in k.lower() for x in ["token", "auth", "pass", "key", "secret", "user", "w", "g"]):
                    redacted_params.append((k, "[REDACTED]"))
                else:
                    redacted_params.append((k, v))
            query = urlencode(redacted_params)
        else:
            query = parsed.query

        # Also check path segments for hash/hex like secrets
        path = parsed.path
        # E.g. /w/yNVuoC49uwRDepuKoF
        path_parts = path.split("/")
        redacted_parts = []
        for part in path_parts:
            if len(part) > 15 and re.match(r"^[a-zA-Z0-9_-]+$", part):
                redacted_parts.append("[REDACTED]")
            else:
                redacted_parts.append(part)
        path = "/".join(redacted_parts)

        return urlunparse((parsed.scheme, netloc, path, parsed.params, query, parsed.fragment))
    except Exception:
        return "[REDACTED_URL]"

def fetch_drogon_data(url: str, description: str) -> bytes:
    """Fetches M3U or EPG from the given URL with a browser-like User-Agent, preventing Xtream calls."""
    if not url:
        raise ValueError(f"Drogon {description} URL is not configured.")

    # Guard against Xtream Codes API attempts
    if "/player_api.php" in url:
        raise ValueError("Security Boundary Violation: Direct Xtream player_api.php paths are blocked.")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        redacted = redact_url(url)
        if e.code == 403:
            raise RuntimeError(
                f"Drogon {description} fetch failed with HTTP 403 Forbidden. "
                "Confirm this URL opens as a raw #EXTM3U playlist or request a direct M3U/Xtream connection from Drogon support. "
                f"Target URL: {redacted}"
            )
        raise RuntimeError(f"Drogon {description} fetch failed: HTTP {e.code}. Target: {redacted}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Drogon {description} service: {str(e)}. Target: {redact_url(url)}")

def parse_m3u_playlist(content: str) -> list:
    """Parses a raw M3U playlist content into normalized JSON channel objects."""
    if not content:
        raise ValueError("Drogon playlist loaded but contains no playable #EXTINF channel entries.")
        
    lines = content.splitlines()
    
    # Validation check
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break
            
    if not first_line.startswith("#EXTM3U"):
        # If it returns HTML/Cloudflare/login
        if "<html" in content.lower() or "<!doctype html" in content.lower():
            raise ValueError(
                "Drogon playlist URL is not returning raw M3U to the local backend. "
                "Confirm this URL opens as a raw #EXTM3U playlist or request a direct M3U/Xtream connection from Drogon support."
            )
        raise ValueError(f"Invalid M3U playlist format: Expected #EXTM3U header, found: '{first_line[:40]}'")

    channels = []
    current_channel = None
    
    # Regex to extract key="value" or key=value attributes
    attr_pattern = re.compile(r'(\S+)\s*=\s*(?:"([^"]*)"|(\S+))')

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("#EXTINF:"):
            # Format: #EXTINF:-1 tvg-id="id" tvg-name="name" tvg-logo="url" group-title="group",Channel Name
            info_part = line[8:]
            comma_idx = info_part.rfind(",")
            if comma_idx != -1:
                attrs_str = info_part[:comma_idx]
                channel_name = info_part[comma_idx+1:].strip()
            else:
                attrs_str = info_part
                channel_name = "Unknown Channel"

            attrs = {}
            for match in attr_pattern.finditer(attrs_str):
                key = match.group(1).lower()
                val = match.group(2) if match.group(2) is not None else match.group(3)
                attrs[key] = val

            current_channel = {
                "name": channel_name,
                "group": attrs.get("group-title", "Uncategorized"),
                "tvgId": attrs.get("tvg-id", ""),
                "tvgName": attrs.get("tvg-name", ""),
                "logo": attrs.get("tvg-logo", ""),
            }
        elif line.startswith("#"):
            # Other directives, ignore
            continue
        else:
            # This is the stream URL
            if current_channel:
                current_channel["streamUrl"] = line
                # Create a stable unique ID based on tvg-id or hashed stream URL
                ch_id = current_channel["tvgId"] or current_channel["tvgName"] or current_channel["name"]
                # Sanitize ID for URLs
                ch_id = re.sub(r'[^a-zA-Z0-9_-]', '_', ch_id)
                if not ch_id or ch_id == "_":
                    ch_id = hashlib.md5(line.encode("utf-8")).hexdigest()[:12]
                
                current_channel["id"] = ch_id
                channels.append(current_channel)
                current_channel = None

    if not channels:
        raise ValueError("Drogon playlist loaded but contains no playable #EXTINF channel entries.")

    return channels

def get_channels_data(force_refresh: bool = False) -> list:
    """Returns the cached or freshly loaded channel list."""
    global _PLAYLIST_CACHE
    config = get_tv_config()
    now = time.time()
    
    if (
        force_refresh or 
        not _PLAYLIST_CACHE["data"] or 
        (now - _PLAYLIST_CACHE["loaded_at"]) > config["playlist_ttl"]
    ):
        _PLAYLIST_CACHE["error"] = None
        try:
            raw_bytes = fetch_drogon_data(config["playlist_url"], "playlist")
            raw_str = raw_bytes.decode("utf-8", errors="ignore")
            channels = parse_m3u_playlist(raw_str)
            
            _PLAYLIST_CACHE["data"] = channels
            _PLAYLIST_CACHE["raw_m3u"] = raw_str
            _PLAYLIST_CACHE["loaded_at"] = now
        except Exception as e:
            _PLAYLIST_CACHE["error"] = str(e)
            if not _PLAYLIST_CACHE["data"]:
                raise
                
    if _PLAYLIST_CACHE["error"] and not _PLAYLIST_CACHE["data"]:
        raise RuntimeError(_PLAYLIST_CACHE["error"])
        
    return _PLAYLIST_CACHE["data"]

def get_raw_playlist(force_refresh: bool = False) -> str:
    """Returns the raw M3U text."""
    get_channels_data(force_refresh)
    return _PLAYLIST_CACHE["raw_m3u"]

def get_epg_xml(force_refresh: bool = False) -> str:
    """Fetches and caches the XMLTV EPG data. Warns on bad XML, but does not block."""
    global _EPG_CACHE
    config = get_tv_config()
    now = time.time()
    
    if (
        force_refresh or 
        not _EPG_CACHE["raw_xml"] or 
        (now - _EPG_CACHE["loaded_at"]) > config["epg_ttl"]
    ):
        _EPG_CACHE["error"] = None
        try:
            raw_bytes = fetch_drogon_data(config["epg_url"], "EPG")
            raw_str = raw_bytes.decode("utf-8", errors="ignore")
            
            # Warn but do not block if it's not valid XML
            if not raw_str.strip().startswith("<?xml") and not raw_str.strip().startswith("<tv"):
                _EPG_CACHE["error"] = "Warning: EPG data does not start with valid XMLTV markers."
            else:
                try:
                    ET.fromstring(raw_bytes)
                except Exception as xml_err:
                    _EPG_CACHE["error"] = f"Warning: EPG XML validation failed: {str(xml_err)}"
            
            _EPG_CACHE["raw_xml"] = raw_str
            _EPG_CACHE["loaded_at"] = now
        except Exception as e:
            _EPG_CACHE["error"] = str(e)
            if not _EPG_CACHE["raw_xml"]:
                raise
                
    return _EPG_CACHE["raw_xml"]
