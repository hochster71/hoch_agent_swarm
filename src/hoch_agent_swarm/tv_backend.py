# -*- coding: utf-8 -*-
"""
tv_backend.py — Backing module for HOCH TV/Drogon.TV M3U and XMLTV integrations.
"""

from __future__ import annotations
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent
CACHE_DIR = PROJECT_ROOT / "data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PLAYLIST_URL = "https://drogon.tv/w/yNVuoC49uwRDepuKoF"
EPG_URL = "https://drogon.tv/g/yNVuoC49uwRDepuKoF"

MOCK_M3U = """#EXTM3U
#EXTINF:-1 tvg-id="news-channel" tvg-name="HOCH News" tvg-logo="https://raw.githubusercontent.com/hjort/logos/master/news.png" group-title="News",HOCH News Live
http://sample.vodobox.com/planete_totale_iphone/planete_totale_iphone.m3u8
#EXTINF:-1 tvg-id="sports-channel" tvg-name="HOCH Sports" tvg-logo="https://raw.githubusercontent.com/hjort/logos/master/sports.png" group-title="Sports",HOCH Sports Live
https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8
#EXTINF:-1 tvg-id="movies-channel" tvg-name="HOCH Movies" tvg-logo="https://raw.githubusercontent.com/hjort/logos/master/movies.png" group-title="Movies",HOCH Movies Live
https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8
"""

MOCK_XMLTV = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="news-channel">
    <display-name>HOCH News</display-name>
  </channel>
  <programme start="20260628000000 +0000" stop="20260628235959 +0000" channel="news-channel">
    <title>Global Security Swarm Report</title>
    <desc>Continuous Monitoring feeds and compliance updates live from the HOCH Swarm.</desc>
  </programme>
  <channel id="sports-channel">
    <display-name>HOCH Sports</display-name>
  </channel>
  <programme start="20260628000000 +0000" stop="20260628235959 +0000" channel="sports-channel">
    <title>Swarm Execution Speedruns</title>
    <desc>Live coverage of autonomous agent pipelines competing for minimum token counts.</desc>
  </programme>
  <channel id="movies-channel">
    <display-name>HOCH Movies</display-name>
  </channel>
  <programme start="20260628000000 +0000" stop="20260628235959 +0000" channel="movies-channel">
    <title>Tears of Steel (Agent Cut)</title>
    <desc>Sci-Fi feature tracking autonomous drones securing high-trust compliance boundaries.</desc>
  </programme>
</tv>
"""


class TVBackend:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.m3u_path = cache_dir / "tv_playlist.m3u"
        self.epg_path = cache_dir / "tv_epg.xml"
        self.last_refreshed: Optional[str] = None
        self.load_cache()

    def load_cache(self, force: bool = False):
        """Downloads files if missing or if forced refresh."""
        if force or not self.m3u_path.exists() or not self.epg_path.exists():
            self.refresh_from_source()
        else:
            m3u_stat = self.m3u_path.stat()
            self.last_refreshed = datetime.fromtimestamp(m3u_stat.st_mtime, timezone.utc).isoformat()

    def refresh_from_source(self):
        """Fetches from Drogon URLs with mock fallbacks on connection issues."""
        import json
        demo_config_path = PROJECT_ROOT / "data" / "demo_config.json"
        tv_offline_mode = False
        if demo_config_path.exists():
            try:
                with open(demo_config_path, "r") as f:
                    tv_offline_mode = json.load(f).get("tv_offline_mode", False)
            except Exception:
                pass

        if tv_offline_mode:
            self.m3u_path.write_text(MOCK_M3U, encoding="utf-8")
            self.epg_path.write_text(MOCK_XMLTV, encoding="utf-8")
            self.last_refreshed = datetime.now(timezone.utc).isoformat()
            return

        # 1. Fetch M3U
        try:
            req = urllib.request.Request(PLAYLIST_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read().decode("utf-8", errors="ignore")
                if content.strip().startswith("#EXTM3U"):
                    self.m3u_path.write_text(content, encoding="utf-8")
        except Exception:
            if not self.m3u_path.exists():
                self.m3u_path.write_text(MOCK_M3U, encoding="utf-8")

        # 2. Fetch EPG
        try:
            req = urllib.request.Request(EPG_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read().decode("utf-8", errors="ignore")
                if "<tv" in content:
                    self.epg_path.write_text(content, encoding="utf-8")
        except Exception:
            if not self.epg_path.exists():
                self.epg_path.write_text(MOCK_XMLTV, encoding="utf-8")

        self.last_refreshed = datetime.now(timezone.utc).isoformat()

    def parse_m3u_playlist(self) -> List[Dict[str, Any]]:
        if not self.m3u_path.exists():
            return []
        
        content = self.m3u_path.read_text(encoding="utf-8", errors="ignore")
        channels = []
        lines = content.splitlines()
        current_channel = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#EXTINF:"):
                current_channel = {}
                tvg_id = re.search(r'tvg-id="([^"]+)"', line)
                tvg_name = re.search(r'tvg-name="([^"]+)"', line)
                tvg_logo = re.search(r'tvg-logo="([^"]+)"', line)
                group_title = re.search(r'group-title="([^"]+)"', line)

                name_parts = line.split(",")
                display_name = name_parts[-1].strip() if name_parts else "Unknown"

                current_channel["tvg_id"] = tvg_id.group(1) if tvg_id else ""
                current_channel["name"] = tvg_name.group(1) if tvg_name else display_name
                current_channel["logo"] = tvg_logo.group(1) if tvg_logo else ""
                current_channel["group"] = group_title.group(1) if group_title else "Uncategorized"
            elif line.startswith("#"):
                continue
            else:
                if current_channel is not None:
                    current_channel["url"] = line
                    ch_id = hashlib.md5(line.encode("utf-8")).hexdigest()[:8]
                    current_channel["id"] = ch_id
                    channels.append(current_channel)
                    current_channel = None

        return channels

    def parse_epg_data(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.epg_path.exists():
            return {}

        epg_data = {}
        try:
            content = self.epg_path.read_text(encoding="utf-8", errors="ignore")
            # Parse XML
            root = ET.fromstring(content)
            for prog in root.findall("programme"):
                channel = prog.get("channel")
                start = prog.get("start")
                stop = prog.get("stop")

                title_el = prog.find("title")
                title = title_el.text if title_el is not None else "No Title"

                desc_el = prog.find("desc")
                desc = desc_el.text if desc_el is not None else ""

                if channel:
                    if channel not in epg_data:
                        epg_data[channel] = []
                    epg_data[channel].append({
                        "start": start,
                        "stop": stop,
                        "title": title,
                        "desc": desc
                    })
        except Exception:
            pass
        return epg_data

    def get_health(self) -> Dict[str, Any]:
        channels = self.parse_m3u_playlist()
        groups = {c["group"] for c in channels}
        return {
            "status": "HEALTHY",
            "channels_count": len(channels),
            "groups_count": len(groups),
            "last_refreshed": self.last_refreshed,
            "compliance_notice": (
                "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW. "
                "The system has ATO-supporting evidence prepared for review. "
                "Actual ATO has not been granted. No authorization claim is being made."
            )
        }


# Singleton TVBackend instance
_tv_backend_instance = None

def get_tv_backend() -> TVBackend:
    global _tv_backend_instance
    if _tv_backend_instance is None:
        _tv_backend_instance = TVBackend()
    return _tv_backend_instance
