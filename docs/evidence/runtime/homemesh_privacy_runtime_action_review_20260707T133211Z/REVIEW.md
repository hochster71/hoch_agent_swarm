# HomeMesh Privacy and Runtime Action Review

## HEAD
3f7fd278006a263969851249df3aa740b6becac4
3f7fd27 Add Brain live combat fleet gateway summaries
b173dbb Harden runtime start stop SQLite writes
0a7d3d5 Harden provider key provisioning script
e1216e2 feat(r1): guided provider API-key provisioning script (opens key page, hidden paste, .env store)
0c50cdc Harden HOCH-200 mission commander truth dashboard
432eb73 fix(pert): wire tests/evidence/accountability/blocked to real sources (UNKNOWN if missing); guard: no hardcoded metric literals

## HomeMesh scoped status
?? backend/homemesh_runtime_asset_graph.py
?? has_live_project_tracker/data/homemesh_manual_devices.json
?? has_live_project_tracker/data/property_schema.json
?? has_live_project_tracker/data/room_schema.json
?? scratch/verify_homemesh_runtime.py
?? scripts/run_homemesh_runtime_burnin.py
?? scripts/test_homemesh_restart_persistence.py
?? scripts/test_stale_device.py
?? scripts/test_unknown_device.py
?? scripts/verify_homemesh_brain_contract.py
?? scripts/verify_homemesh_brain_live_query.py
?? tests/e2e/has-hasf-homemesh-runtime-freshness.spec.ts
?? tests/e2e/has-hasf-homemesh-spatial-graph.spec.ts
?? tests/test_homemesh_spatial_graph.py

## Runtime-action scan
628:        res = subprocess.run(["arp", "-a"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
--- backend/homemesh_runtime_asset_graph.py
24:        res = subprocess.run(["lsof", "-t", "-iTCP:8000", "-sTCP:LISTEN"], stdout=subprocess.PIPE, text=True)
85:                res_brain = subprocess.run(["python3", "scripts/verify_homemesh_brain_live_query.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
--- scripts/run_homemesh_runtime_burnin.py
102:        subprocess.run(["./scripts/" + "stop_has_" + "runtime.sh"], check=True, cwd=str(ROOT))
103:        subprocess.run(["./scripts/" + "install_launch" + "d_supervisor.sh"], check=True, cwd=str(ROOT))
164:        subprocess.run(["python3", "scripts/verify_homemesh_brain_live_query.py"], check=True, cwd=str(ROOT))
--- scripts/test_homemesh_restart_persistence.py

## Privacy / home-location scan
45:    mac_address: str
46:    ip_address: str
48:    ssid_list: List[str]
53:    mac_address: str
54:    ip_address: str
61:    mac_address: str
62:    ip_address: str
64:    wan_ip: str
85:class Parcel(BaseModel):
86:    parcel_id: str
87:    county: str = "Madison"
88:    state: str = "Alabama"
89:    owner_name: str = "REDACTED_OWNER"
90:    legal_description: str
92:    latitude: float
93:    longitude: float
122:    mac_address: str
163:                mac_address TEXT NOT NULL,
166:                ip_address TEXT,
172:                ssid TEXT,
200:                ip_address TEXT,
201:                mac_address TEXT,
211:                mac_address TEXT PRIMARY KEY,
212:                ip_address TEXT,
246:                mac_address TEXT,
296:            obs_id = obs.get("id") or f"obs-{obs.get('mac_address')}-{obs.get('timestamp')}"
300:                    hostname, ip_address, mac_address, vendor, raw_summary, confidence_score, trust_score
304:                obs.get("device_id") or f"dev-{obs.get('mac_address').replace(':', '')}",
310:                obs.get("mac_address").lower(),
340:                "mac_address": r[7],
356:                    id, mac_address, hostname, display_name, ip_address, vendor, device_type,
357:                    os_guess, owner, vlan, ssid, connected_to, room_id, zone_id, trust_score,
367:                dev.get("ip_address"),
373:                dev.get("ssid"),
406:                "mac_address": mac,
409:                "ip_address": r[4],
415:                "ssid": r[10],
443:                    mac_address, ip_address, hostname, first_seen, last_seen, evidence_sources
446:                u["mac_address"].lower(),
447:                u.get("ip_address"),
474:            mac = dev["mac_address"]
491:                    "reason": f"Discovered on network with IP {dev.get('ip_address') or 'unknown'}. Placed in unmapped_devices room (fail-closed).",
492:                    "mac_address": mac,
545:                "mac_address": r[0],
546:                "ip_address": r[1],
597:def db_save_policy_decision(device_id: str, mac_address: str, classification: str, trust_score: float, decision: str, reason: str):
602:                decision_id, timestamp, device_id, mac_address, classification, trust_score, decision, reason
608:            mac_address.lower(),
642:                        "mac_address": mac,
659:            matches = re.findall(r'ip_address=([\d\.]+).*?hw_address=1,([0-9a-fA-F:]+)', content, re.DOTALL)
667:                    "mac_address": mac_formatted,
676:            {"ip": "10.0.0.91", "mac": "44:55:66:77:88:99", "hostname": "michaels-ipad-mini.local"},
677:            {"ip": "10.0.0.75", "mac": "22:33:44:55:66:77", "hostname": "quest-3-xr.local"}
685:                "mac_address": lease["mac"],
704:            "mac_address": "22:33:44:55:66:77",
705:            "observed_ip": "10.0.0.75",
715:            "mac_address": "44:55:66:77:88:99",
716:            "observed_ip": "10.0.0.91",
746:                "mac_address": "unknown_ssdp",
760:        "mac_address": "00:11:22:33:44:55",
761:        "observed_ip": "10.0.0.50",
786:                "mac_address": "fc:ec:da:01:02:03",
787:                "observed_ip": "10.0.0.1",
797:                "mac_address": "fc:ec:da:04:05:06",
798:                "observed_ip": "10.0.0.10",
835:            essid = c.get("essid", "")
843:                "mac_address": mac.lower(),
847:                "details": {"ap_mac": ap_mac, "sw_mac": sw_mac, "essid": essid, "vlan": vlan}
871:                "mac_address": "11:22:33:44:55:66",
872:                "observed_ip": "10.0.0.200",
897:            mac = attrs.get("mac") or attrs.get("mac_address")
898:            ip = attrs.get("ip") or attrs.get("ip_address")
906:                    "mac_address": mac.lower(),
928:        if dev.get("mac_address") == mac:
951:    """Merges all evidence observations by MAC address into RECONCILED_DEVICES"""
960:        mac = dev["mac_address"].lower()
965:            "mac_address": mac,
966:            "ip_address": dev["ip_address"],
972:            "ssid": dev["ssid"],
989:        mac = obs["mac_address"].lower()
1001:                if alert.get("mac_address") == mac:
1010:                    "mac_address": mac,
1020:                "mac_address": mac,
1021:                "ip_address": ip,
1027:                "ssid": "unknown",
1061:                if ip and dev["ip_address"] != ip:
1062:                    dev["ip_address"] = ip
1142:                "mac_address": mac,
1143:                "ip_address": dev["ip_address"],
1180:        {"id": "udm-pro", "label": "UDM Pro Router", "type": "router", "ip": "10.0.0.1"},
1181:        {"id": "switch-main", "label": "UniFi 24-Port Switch", "type": "switch", "ip": "10.0.0.2"},
1182:        {"id": "ap-office", "label": "AP Office", "type": "access_point", "ip": "10.0.0.10"},
1183:        {"id": "ap-living-room", "label": "AP Living Room", "type": "access_point", "ip": "10.0.0.11"}
1197:            "ip": dev["ip_address"]
1230:    mac = payload.get("mac_address", "").lower()
1235:        raise HTTPException(status_code=400, detail="Missing mac_address or room_id")
1241:        if dev["mac_address"].lower() == mac:
1255:            "mac_address": mac,
1256:            "ip_address": payload.get("ip_address", "10.0.0.199"),
1262:            "ssid": "REDACTED_SECURE_SSID",
1304:            "parcel": {
1305:              "parcel_id": "REDACTED-PARCEL-ID",
1306:              "county": "Madison",
1307:              "state": "Alabama",
1308:              "owner_name": "REDACTED_OWNER",
1309:              "legal_description": "REDACTED_LEGAL_DESCRIPTION",
1312:                "latitude": 0.0,
1313:                "longitude": 0.0
1836:                <h2>Madison County Property Context</h2>
1837:                <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Legal and spatial parcel metadata registry.</p>
1841:                            <label>Parcel ID</label>
1842:                            <span id="prop-parcel-id">N/A</span>
1853:                            <label>GIS Coordinates (Latitude/Longitude)</label>
1890:                                <th>IP Address</th>
1891:                                <th>MAC Address</th>
1914:                                <th>MAC Address</th>
2037:                {x: 100, y: 220, type: 'router', id: 'udm-pro', label: 'UDM Pro', ip: '10.0.0.1'},
2038:                {x: 280, y: 220, type: 'switch', id: 'switch-main', label: 'Main Switch', ip: '10.0.0.2'},
2039:                {x: 460, y: 120, type: 'access_point', id: 'ap-office', label: 'AP Office', ip: '10.0.0.10'},
2040:                {x: 460, y: 320, type: 'access_point', id: 'ap-living-room', label: 'AP Living', ip: '10.0.0.11'}
2077:                    <p>${esc(dev.ip_address)}</p>
2099:                <div class="hover-card-row"><span>IP:</span><span>${esc(dev.ip_address)}</span></div>
2100:                <div class="hover-card-row"><span>MAC:</span><span>${esc(dev.mac_address)}</span></div>
2102:                <div class="hover-card-row"><span>VLAN/SSID:</span><span>${esc(dev.vlan)} / ${esc(dev.ssid)}</span></div>
2143:            if (!propertyData || !propertyData.parcel) return;
2144:            const p = propertyData.parcel;
2145:            document.getElementById('prop-parcel-id').textContent = p.parcel_id;
2146:            document.getElementById('prop-legal').textContent = p.legal_description;
2148:            document.getElementById('prop-coords').textContent = `Lat: ${p.gis_coordinates.latitude}, Lng: ${p.gis_coordinates.longitude}`;
2208:                        <td>${esc(dev.ip_address)}</td>
2209:                        <td>${esc(dev.mac_address)}</td>
2213:                            <select onchange="mapDevice('${dev.mac_address}', this.value)" style="padding:4px; border-radius:4px; background:var(--bg-card); color:var(--text-primary); border:1px solid var(--border-color);">
2234:                    body: JSON.stringify({mac_address: mac, room_id: roomId})
2257:                        <td>${esc(obs.mac_address)}</td>
--- backend/homemesh_runtime_asset_graph.py
6:    "mac_address": "aa:bb:cc:dd:ee:ff",
7:    "ip_address": "10.0.0.120",
13:    "ssid": "REDACTED_SECURE_SSID",
40:    "mac_address": "00:11:22:33:44:55",
41:    "ip_address": "10.0.0.50",
47:    "ssid": "REDACTED_IOT_SSID",
73:    "mac_address": "44:55:66:77:88:99",
74:    "ip_address": "10.0.0.199",
80:    "ssid": "REDACTED_SECURE_SSID",
--- has_live_project_tracker/data/homemesh_manual_devices.json
4:  "description": "Defines property, parcel, and structure metadata for the residence.",
7:    "parcel": {
10:        "parcel_id": { "type": "STRING" },
11:        "county": { "type": "STRING", "default": "Madison" },
12:        "state": { "type": "STRING", "default": "Alabama" },
13:        "owner_name": { "type": "STRING", "default": "REDACTED_OWNER" },
14:        "legal_description": { "type": "STRING" },
19:            "latitude": { "type": "NUMBER" },
20:            "longitude": { "type": "NUMBER" }
22:          "required": ["latitude", "longitude"]
26:      "required": ["parcel_id", "county", "state", "owner_name"]
78:  "required": ["parcel", "structures", "exterior_zones", "interior_zones", "confidence_level", "source_references"]
--- has_live_project_tracker/data/property_schema.json

## Safe core compile

## Focused HomeMesh unit tests
.......                                                                  [100%]
7 passed in 0.23s

## Runtime containment
Containment CLEAN
