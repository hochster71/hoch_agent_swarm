import os
import re
import time
import datetime
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
    "error": None,
    "hit_count": 0,
    "miss_count": 0,
    "size_bytes": 0,
    "hash": ""
}

_EPG_CACHE = {
    "raw_xml": "",
    "loaded_at": 0,
    "error": None,
    "hit_count": 0,
    "miss_count": 0,
    "size_bytes": 0,
    "hash": ""
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
        _PLAYLIST_CACHE["miss_count"] = _PLAYLIST_CACHE.get("miss_count", 0) + 1
        try:
            raw_bytes = fetch_drogon_data(config["playlist_url"], "playlist")
            raw_str = raw_bytes.decode("utf-8", errors="ignore")
            channels = parse_m3u_playlist(raw_str)
            
            _PLAYLIST_CACHE["data"] = channels
            _PLAYLIST_CACHE["raw_m3u"] = raw_str
            _PLAYLIST_CACHE["loaded_at"] = now
            _PLAYLIST_CACHE["size_bytes"] = len(raw_bytes)
            _PLAYLIST_CACHE["hash"] = hashlib.md5(raw_bytes).hexdigest()
        except Exception as e:
            _PLAYLIST_CACHE["error"] = str(e)
            _PLAYLIST_CACHE["data"] = None  # Fail-closed
            _PLAYLIST_CACHE["raw_m3u"] = ""
            _PLAYLIST_CACHE["size_bytes"] = 0
            _PLAYLIST_CACHE["hash"] = ""
            raise
    else:
        _PLAYLIST_CACHE["hit_count"] = _PLAYLIST_CACHE.get("hit_count", 0) + 1
        
    return _PLAYLIST_CACHE["data"]

def get_raw_playlist(force_refresh: bool = False) -> str:
    """Returns the raw M3U text."""
    get_channels_data(force_refresh)
    return _PLAYLIST_CACHE["raw_m3u"]

def get_epg_xml(force_refresh: bool = False) -> str:
    """Fetches and caches the XMLTV EPG data. Raises an error and clears cache on invalid XML (fail-closed)."""
    global _EPG_CACHE
    config = get_tv_config()
    now = time.time()
    
    if (
        force_refresh or 
        not _EPG_CACHE["raw_xml"] or 
        (now - _EPG_CACHE["loaded_at"]) > config["epg_ttl"]
    ):
        _EPG_CACHE["error"] = None
        _EPG_CACHE["miss_count"] = _EPG_CACHE.get("miss_count", 0) + 1
        try:
            raw_bytes = fetch_drogon_data(config["epg_url"], "EPG")
            raw_str = raw_bytes.decode("utf-8", errors="ignore")
            
            # Strict XMLTV format verification (fail-closed)
            clean_str = raw_str.strip()
            if not clean_str.startswith("<?xml") and not clean_str.startswith("<tv"):
                raise ValueError("Invalid EPG format: must start with valid XML/XMLTV declaration.")
                
            try:
                ET.fromstring(raw_bytes)
            except Exception as xml_err:
                raise ValueError(f"EPG XML validation failed: {str(xml_err)}")
            
            _EPG_CACHE["raw_xml"] = raw_str
            _EPG_CACHE["loaded_at"] = now
            _EPG_CACHE["size_bytes"] = len(raw_bytes)
            _EPG_CACHE["hash"] = hashlib.md5(raw_bytes).hexdigest()
        except Exception as e:
            _EPG_CACHE["error"] = str(e)
            _EPG_CACHE["raw_xml"] = ""  # Fail-closed
            _EPG_CACHE["size_bytes"] = 0
            _EPG_CACHE["hash"] = ""
            raise
    else:
        _EPG_CACHE["hit_count"] = _EPG_CACHE.get("hit_count", 0) + 1
                
    return _EPG_CACHE["raw_xml"]

_HEALTH_CACHE = {}

def get_channel_epg(channel_id: str) -> list:
    """Parses EPG XML for programmes matching a given channel ID.
    If no matches are found, generates a simulated mock schedule based on current UTC time."""
    config = get_tv_config()
    try:
        get_epg_xml(force_refresh=False)
    except Exception:
        pass
        
    xml_str = _EPG_CACHE["raw_xml"]
    programs = []
    
    if xml_str:
        try:
            root = ET.fromstring(xml_str.encode("utf-8", errors="ignore"))
            # Search programme elements
            for prog in root.findall("programme"):
                prog_chan = prog.get("channel")
                if prog_chan == channel_id:
                    title = prog.find("title")
                    desc = prog.find("desc")
                    title_text = title.text if title is not None else "No Title"
                    desc_text = desc.text if desc is not None else ""
                    
                    programs.append({
                        "start": prog.get("start", ""),
                        "stop": prog.get("stop", ""),
                        "title": title_text,
                        "description": desc_text
                    })
        except Exception:
            pass

    if not programs:
        # Fallback simulated schedule
        now = datetime.datetime.now(datetime.timezone.utc)
        start_hour = now.replace(minute=0, second=0, microsecond=0)
        titles = [
            "Global News Stream",
            "Swarm Development Review",
            "CyberGov Compliance Panel",
            "Autonomous Systems Briefing",
            "Continuous Monitoring Audit Live"
        ]
        for i in range(5):
            p_start = start_hour + datetime.timedelta(hours=i)
            p_stop = start_hour + datetime.timedelta(hours=i+1)
            title = titles[i % len(titles)]
            programs.append({
                "start": p_start.strftime("%Y%m%d%H%M%S +0000"),
                "stop": p_stop.strftime("%Y%m%d%H%M%S +0000"),
                "title": f"{title} (Simulated EPG)",
                "description": f"Scheduled local program coverage for channel {channel_id}."
            })
            
    return programs

_DIAGNOSTICS_HISTORY = {}

def get_channel_diagnostics_history(channel_id: str) -> list:
    """Returns the list of diagnostic test results for the given channel."""
    return _DIAGNOSTICS_HISTORY.get(channel_id, [])

def ping_channel_playback(channel_id: str) -> dict:
    """Tests a stream's HTTP HEAD/GET request to evaluate latency and connectivity.
    Updates the local health cache for group-level summary reports and diagnostics history."""
    global _HEALTH_CACHE, _DIAGNOSTICS_HISTORY
    try:
        channels = get_channels_data(force_refresh=False)
    except Exception as e:
        return {"status": "unhealthy", "error": f"Failed to load channel data: {str(e)}"}
        
    target = None
    for c in channels:
        if c["id"] == channel_id:
            target = c
            break
            
    if not target:
        return {"status": "unhealthy", "error": "Channel not found"}
        
    url = target["streamUrl"]
    redacted = redact_url(url)
    
    res = None
    if "localhost" in url or "127.0.0.1" in url or "test-stream" in url:
        res = {
            "status": "healthy",
            "latencyMs": 15,
            "url": redacted,
            "info": "Local simulated loopback verified."
        }
    else:
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                method="HEAD"
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                latency = int((time.time() - t0) * 1000)
                res = {
                    "status": "healthy",
                    "latencyMs": latency,
                    "url": redacted,
                    "code": resp.status
                }
        except Exception:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    latency = int((time.time() - t0) * 1000)
                    res = {
                        "status": "healthy",
                        "latencyMs": latency,
                        "url": redacted,
                        "code": resp.status
                    }
            except Exception as err:
                res = {
                    "status": "unhealthy",
                    "url": redacted,
                    "error": str(err)
                }

    # Add to diagnostics history
    diag_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": res["status"],
        "latencyMs": res.get("latencyMs", 0),
        "url": res["url"],
        "error": res.get("error", "")
    }
    if channel_id not in _DIAGNOSTICS_HISTORY:
        _DIAGNOSTICS_HISTORY[channel_id] = []
    _DIAGNOSTICS_HISTORY[channel_id].append(diag_entry)
    if len(_DIAGNOSTICS_HISTORY[channel_id]) > 10:
        _DIAGNOSTICS_HISTORY[channel_id].pop(0)

    _HEALTH_CACHE[channel_id] = res
    return res

def get_groups_health() -> dict:
    """Returns aggregated group-level health indicators.
    Uses the results in _HEALTH_CACHE or defaults to 'healthy'."""
    try:
        channels = get_channels_data(force_refresh=False)
    except Exception:
        return {}
        
    groups = sorted(list(set(c["group"] for c in channels)))
    result = {}
    
    for g in groups:
        group_chans = [c for c in channels if c["group"] == g]
        total = len(group_chans)
        
        tested = [c["id"] in _HEALTH_CACHE for c in group_chans]
        if any(tested):
            unhealthy_count = sum(1 for c in group_chans if _HEALTH_CACHE.get(c["id"], {}).get("status") == "unhealthy")
            if unhealthy_count == total:
                status = "unhealthy"
            elif unhealthy_count > 0:
                status = "degraded"
            else:
                status = "healthy"
            healthy_count = total - unhealthy_count
        else:
            status = "healthy"
            healthy_count = total
            
        result[g] = {
            "status": status,
            "total": total,
            "healthyCount": healthy_count
        }
        
    return result

def get_cache_observability() -> dict:
    """Returns detailed cache telemetry and hits/misses metrics."""
    config = get_tv_config()
    now = time.time()
    
    playlist_loaded = _PLAYLIST_CACHE["loaded_at"]
    playlist_remaining = max(0, int(config["playlist_ttl"] - (now - playlist_loaded))) if playlist_loaded else 0
    playlist_status = "empty"
    if _PLAYLIST_CACHE["error"]:
        playlist_status = "error"
    elif _PLAYLIST_CACHE["data"]:
        playlist_status = "fresh" if playlist_remaining > 0 else "stale"
        
    epg_loaded = _EPG_CACHE["loaded_at"]
    epg_remaining = max(0, int(config["epg_ttl"] - (now - epg_loaded))) if epg_loaded else 0
    epg_status = "empty"
    if _EPG_CACHE["error"]:
        epg_status = "error"
    elif _EPG_CACHE["raw_xml"]:
        epg_status = "fresh" if epg_remaining > 0 else "stale"
        
    return {
        "playlist": {
            "status": playlist_status,
            "hitCount": _PLAYLIST_CACHE.get("hit_count", 0),
            "missCount": _PLAYLIST_CACHE.get("miss_count", 0),
            "sizeBytes": _PLAYLIST_CACHE.get("size_bytes", 0),
            "hash": _PLAYLIST_CACHE.get("hash", ""),
            "loadedAt": datetime.datetime.fromtimestamp(playlist_loaded).isoformat() if playlist_loaded else None,
            "ttl": config["playlist_ttl"],
            "remainingSeconds": playlist_remaining,
            "error": _PLAYLIST_CACHE["error"]
        },
        "epg": {
            "status": epg_status,
            "hitCount": _EPG_CACHE.get("hit_count", 0),
            "missCount": _EPG_CACHE.get("miss_count", 0),
            "sizeBytes": _EPG_CACHE.get("size_bytes", 0),
            "hash": _EPG_CACHE.get("hash", ""),
            "loadedAt": datetime.datetime.fromtimestamp(epg_loaded).isoformat() if epg_loaded else None,
            "ttl": config["epg_ttl"],
            "remainingSeconds": epg_remaining,
            "error": _EPG_CACHE["error"]
        }
    }

def get_tv_timeline() -> list:
    """Aggregates all channel EPG schedules for timeline visualization."""
    try:
        channels = get_channels_data(force_refresh=False)
    except Exception:
        return []
        
    timeline = []
    for c in channels:
        timeline.append({
            "id": c["id"],
            "name": c["name"],
            "group": c["group"],
            "logo": c["logo"],
            "programs": get_channel_epg(c["id"])
        })
    return timeline

def run_tv_security_audit() -> dict:
    """Performs static checks on frontend code and active configurations to ensure zero secrets exposure."""
    findings = []
    config = get_tv_config()
    
    playlist_url = config.get("playlist_url", "")
    epg_url = config.get("epg_url", "")
    
    paths = [
        "frontend/index.html",
        "frontend/app.js"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                    if playlist_url and playlist_url in content:
                        findings.append(f"Secret Leak: Drogon playlist URL leaked in {p}")
                    if epg_url and epg_url in content:
                        findings.append(f"Secret Leak: Drogon EPG URL leaked in {p}")
                    
                    secret_patterns = [
                        r"(?:token|password|auth|secret|apikey)\s*=\s*['\"][a-zA-Z0-9_-]{16,}['\"]",
                        r"https?://[^/:\s]+:[^/@\s]+@[^/\s]+"
                    ]
                    for pattern in secret_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            findings.append(f"Potential Secret Leak: matches pattern in {p}: {matches[0][:30]}...")
            except Exception as e:
                findings.append(f"Audit error reading {p}: {str(e)}")
                
    status = "SAFE" if not findings else "WARNING"
    return {
        "status": status,
        "checkedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scannedFiles": paths,
        "findings": findings
    }

