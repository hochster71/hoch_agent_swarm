**Local Compute Resources Audit Report**

**Discovered Assets:**

1. **Asset ID:** SW-001
	* Host Name: Server01
	* IP Address: 10.0.0.1
	* Operating System: Windows Server 2019
	* CPU Cores: 8
	* Memory (GB): 64
2. **Asset ID:** SW-002
	* Host Name: Server02
	* IP Address: 10.0.0.2
	* Operating System: Linux Ubuntu 20.04
	* CPU Cores: 16
	* Memory (GB): 128
3. **Asset ID:** SW-003
	* Host Name: Desktop01
	* IP Address: 10.0.0.3
	* Operating System: Windows 10 Pro
	* CPU Cores: 4
	* Memory (GB): 16

**Active Dynamic Leases:**

1. **Asset ID:** SW-001
	* Lease Type: Server
	* Lease Duration: 8760h
	* Reserved Resources:
		+ Storage: 100GB SSD
		+ Network: 10GbE
2. **Asset ID:** SW-002
	* Lease Type: Worker Node
	* Lease Duration: 720h
	* Reserved Resources:
		+ CPU: 1 core reserved for high-priority tasks
		+ Memory: 32GB reserved for task memory allocation

**Device Capability Sets:**

1. **Asset ID:** SW-001
	* Capabilities:
		+ Disk I/O: High-bandwidth disk access
		+ Network: High-speed network connectivity (10GbE)
2. **Asset ID:** SW-002
	* Capabilities:
		+ CPU Compute: Multi-threaded compute capabilities
		+ Memory Access: Direct memory access for high-performance tasks
3. **Asset ID:** SW-003
	* Capabilities:
		+ Display Output: High-resolution display output (3840x2160)
		+ USB Port: Multiple USB ports for device connectivity

**Connection Health Verification:**

All discovered assets exhibit healthy connections, with no signs of network congestion or other issues.

---

**Audit Completion Summary:**

The local compute resources audit has been completed successfully. The following assets have been identified:

1. Server01 (SW-001)
	* Hosted on 10.0.0.1
	* Operating System: Windows Server 2019
	* Asset Type: Server
2. Server02 (SW-002)
	* Hosted on 10.0.0.2
	* Operating System: Linux Ubuntu 20.04
	* Asset Type: Worker Node
3. Desktop01 (SW-003)
	* Hosted on 10.0.0.3
	* Operating System: Windows 10 Pro
	* Asset Type: Client Device

Active dynamic leases have been identified for Server01 and Server02, while device capability sets have been mapped for all three assets.

This marks the completion of the audit task.