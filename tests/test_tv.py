import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.tv_manager import (
    parse_m3u_playlist, 
    get_channels_data, 
    get_raw_playlist, 
    get_epg_xml,
    get_channel_epg,
    ping_channel_playback,
    get_groups_health
)

client = TestClient(app)

def test_m3u_parsing_local():
    # Test M3U parsing from string content
    sample_m3u = """#EXTM3U
#EXTINF:-1 tvg-id="cnn" tvg-name="CNN" tvg-logo="http://example.com/cnn.png" group-title="News",CNN US
http://localhost:8080/cnn/index.m3u8
#EXTINF:-1 tvg-id="hbo" tvg-name="HBO" group-title="Movies",HBO HD
http://localhost:8080/hbo/index.m3u8
"""
    channels = parse_m3u_playlist(sample_m3u)
    assert len(channels) == 2
    assert channels[0]["name"] == "CNN US"
    assert channels[0]["group"] == "News"
    assert channels[0]["logo"] == "http://example.com/cnn.png"
    assert channels[0]["streamUrl"] == "http://localhost:8080/cnn/index.m3u8"
    assert channels[1]["name"] == "HBO HD"
    assert channels[1]["group"] == "Movies"
    assert channels[1]["streamUrl"] == "http://localhost:8080/hbo/index.m3u8"

def test_tv_endpoints():
    # Get initial groups
    resp = client.get("/api/tv/groups")
    assert resp.status_code == 200
    groups = resp.json()
    assert isinstance(groups, list)
    
    # Get channels list
    resp = client.get("/api/tv/channels")
    assert resp.status_code == 200
    channels = resp.json()
    assert isinstance(channels, list)
    
    # Get health diagnostics
    resp = client.get("/api/tv/health")
    assert resp.status_code == 200
    health = resp.json()
    assert "ok" in health
    assert "channelCount" in health
    assert "epgConfigured" in health
    assert "playlistLoadedAt" in health
    
    # Validate no blocked/unauthorized claims exist in response
    blocked_claims = [
        "Public service operational",
        "Externally exposed production service",
        "Authorized to Operate",
        "ATO granted",
        "Risk eliminated",
        "100% secure"
    ]
    data_str = str(health).lower()
    for claim in blocked_claims:
        assert claim.lower() not in data_str

def test_tv_epg_and_diagnostics():
    # Load EPG guide for a simulated channel
    resp = client.get("/api/tv/channel/cnn/epg")
    assert resp.status_code == 200
    epg = resp.json()
    assert isinstance(epg, list)
    assert len(epg) > 0
    assert "title" in epg[0]
    assert "description" in epg[0]
    
    # Run a playback diagnostic test
    resp = client.post("/api/tv/channel/cnn/test")
    assert resp.status_code == 200
    diag = resp.json()
    assert "status" in diag
    
    # Get group health stats
    resp = client.get("/api/tv/groups/health")
    assert resp.status_code == 200
    ghealth = resp.json()
    assert isinstance(ghealth, dict)

