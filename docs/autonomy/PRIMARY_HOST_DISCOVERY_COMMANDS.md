# Primary Host Discovery Commands

This guide details safe local diagnostic commands to scan the LAN and verify eligible always-on candidates.

---

## 1. Capture ARP Table
To inspect MAC-to-IP address mapping on the local segment:
```bash
arp -a
```

---

## 2. Scan active LAN IPs for Open SSH (Port 22)
Iterate over the active IPs to check which host is listening on SSH:
```bash
for ip in 10.0.0.1 10.0.0.7 10.0.0.13 10.0.0.21 10.0.0.22 10.0.0.26 10.0.0.30 10.0.0.41 10.0.0.63 10.0.0.90 10.0.0.96 10.0.0.98 10.0.0.129 10.0.0.145 10.0.0.157 10.0.0.169; do nc -w 1 -z "$ip" 22 && echo "$ip SSH port 22 is OPEN"; done
```

---

## 3. Perform Reverse DNS / mDNS Lookup
Iterate over active IPs to resolve hostnames:
```bash
for ip in 10.0.0.1 10.0.0.7 10.0.0.13 10.0.0.21 10.0.0.22 10.0.0.26 10.0.0.30 10.0.0.41 10.0.0.63 10.0.0.90 10.0.0.96 10.0.0.98 10.0.0.129 10.0.0.145 10.0.0.157 10.0.0.169; do host "$ip" || true; done
```

---

## 4. SSH Host Identity Verification
For any candidate that has SSH port 22 open (e.g. `10.0.0.13`), check hostname and OS parameters:
```bash
ssh -o BatchMode=yes -o ConnectTimeout=2 michaelhoch@10.0.0.13 "hostname && uname -a"
```
