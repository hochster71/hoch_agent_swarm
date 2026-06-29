import sqlite3
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

DEVICES = [
    {"device_id": "vivint_camera_1", "name": "Front Door Vivint Camera", "type": "camera"},
    {"device_id": "rachio_controller", "name": "Rachio Sprinkler Controller", "type": "irrigation"},
    {"device_id": "pentair_pool", "name": "Pentair Pool Control ScreenLogic", "type": "pool"},
    {"device_id": "tesla_energy", "name": "Tesla PowerShare Gateway", "type": "energy"}
]

def register_all_devices():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    
    try:
        # Populate device capabilities
        capabilities = [
            ("vivint_camera_1", "get_live_feed", 1, "vivint_adapter", "A1", 1, 0),
            ("vivint_camera_1", "talkback", 1, "vivint_adapter", "A7", 0, 1),
            ("rachio_controller", "get_watering_schedule", 1, "rachio_adapter", "A0", 1, 0),
            ("rachio_controller", "trigger_watering", 1, "rachio_adapter", "A5", 0, 1),
            ("pentair_pool", "get_pool_temp", 1, "pentair_adapter", "A0", 1, 0),
            ("pentair_pool", "activate_spa", 1, "pentair_adapter", "A6", 0, 1),
            ("tesla_energy", "get_backup_charge", 1, "tesla_energy_adapter", "A0", 1, 0),
            ("tesla_energy", "set_backup_reserve", 1, "tesla_energy_adapter", "A6", 0, 1)
        ]
        
        for c in capabilities:
            conn.execute("""
                INSERT OR REPLACE INTO device_capabilities 
                (device_id, capability, available, source, risk_class, read_only, requires_approval, last_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (c[0], c[1], c[2], c[3], c[4], c[5], c[6], now_iso()))
            
        conn.commit()
    finally:
        conn.close()

# Register devices
register_all_devices()
