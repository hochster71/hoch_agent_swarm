import pytest
from backend.apple_telemetry.collector import (
    get_local_mac_details,
    get_paired_devices_status,
    collect_and_store_apple_telemetry,
    get_cached_apple_telemetry,
    get_db_conn
)

def test_get_local_mac_details():
    res = get_local_mac_details()
    assert res["device_id"] == "macbook_pro_local"
    assert "MacBook" in res["device_type"]
    assert 0 <= res["battery_percent"] <= 100
    assert res["charging_state"] in ("charging", "discharging", "charged")
    assert 0 <= res["memory_usage_percent"] <= 100
    assert 0 <= res["disk_usage_percent"] <= 100
    assert 0 <= res["cpu_load_percent"] <= 100
    assert res["uptime_seconds"] > 0
    assert "macOS" in res["os_version"]
    assert res["available_storage_gb"] >= 0

def test_get_paired_devices_status():
    res = get_paired_devices_status()
    assert len(res) == 5
    types = [d["device_type"] for d in res]
    assert "iMac" in types
    assert "iPhone" in types
    assert "iPad" in types
    assert "Apple Watch" in types
    assert "AirPods" in types

def test_collect_and_store_apple_telemetry():
    res = collect_and_store_apple_telemetry()
    assert len(res) == 6
    
    # Check SQLite store
    conn = get_db_conn()
    try:
        rows = conn.execute("SELECT * FROM apple_device_telemetry").fetchall()
        assert len(rows) == 6
        local_mac = conn.execute("SELECT * FROM apple_device_telemetry WHERE device_id = 'macbook_pro_local'").fetchone()
        assert local_mac is not None
        assert local_mac["device_type"] == "MacBook Pro"
    finally:
        conn.close()

def test_get_cached_apple_telemetry():
    res = get_cached_apple_telemetry()
    assert len(res) == 6
