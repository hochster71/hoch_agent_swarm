# -*- coding: utf-8 -*-
"""
test_tv.py — Test suite for HOCH TV/Drogon.TV integration.
"""

from __future__ import annotations
import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from hoch_agent_swarm.tv_backend import TVBackend, MOCK_M3U, MOCK_XMLTV
from hoch_agent_swarm.ui_server import app

def test_m3u_parsing():
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        backend = TVBackend(cache_dir=cache_dir)
        
        # Test default load creates mock fallback if empty
        assert backend.m3u_path.exists()
        assert backend.epg_path.exists()
        
        channels = backend.parse_m3u_playlist()
        assert len(channels) > 0
        for ch in channels:
            assert "id" in ch
            assert "name" in ch
            assert "url" in ch
            assert "group" in ch
            assert "logo" in ch

def test_xmltv_parsing():
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        backend = TVBackend(cache_dir=cache_dir)
        
        epg = backend.parse_epg_data()
        assert len(epg) > 0
        # Check that program listings exist for mock channels
        assert "news-channel" in epg
        news_programs = epg["news-channel"]
        assert len(news_programs) > 0
        assert news_programs[0]["title"] == "Global Security Swarm Report"

def test_tv_endpoints():
    with app.test_client() as client:
        # 1. Health endpoint
        res = client.get("/api/tv/health")
        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert data["status"] == "HEALTHY"
        assert "channels_count" in data
        assert "groups_count" in data
        assert "compliance_notice" in data
        assert "ATO-SUPPORTING EVIDENCE" in data["compliance_notice"]
        
        # 2. Groups endpoint
        res = client.get("/api/tv/groups")
        assert res.status_code == 200
        groups = json.loads(res.data.decode("utf-8"))
        assert len(groups) > 0
        first_group = groups[0]
        
        # 3. Channels endpoint
        res = client.get("/api/tv/channels")
        assert res.status_code == 200
        channels = json.loads(res.data.decode("utf-8"))
        assert len(channels) > 0
        
        # Test filtering by group
        res = client.get(f"/api/tv/channels?group={first_group}")
        assert res.status_code == 200
        group_channels = json.loads(res.data.decode("utf-8"))
        assert len(group_channels) > 0
        for ch in group_channels:
            assert ch["group"] == first_group

        # 4. Specific channel info
        ch_id = channels[0]["id"]
        res = client.get(f"/api/tv/channel/{ch_id}")
        assert res.status_code == 200
        channel_info = json.loads(res.data.decode("utf-8"))
        assert channel_info["id"] == ch_id
        assert "epg" in channel_info

        # 5. Raw M3U endpoint
        res = client.get("/api/tv/playlist.m3u")
        assert res.status_code == 200
        assert res.mimetype == "audio/x-mpegurl"
        assert b"#EXTM3U" in res.data

        # 6. Raw XML endpoint
        res = client.get("/api/tv/epg.xml")
        assert res.status_code == 200
        assert res.mimetype == "application/xml"
        assert b"<tv" in res.data
