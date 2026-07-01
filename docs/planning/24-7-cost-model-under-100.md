# Planning: 24/7 Cost Model Under $100/Month

## 1. Cost Ceiling & Constraints
To ensure 24/7 operability without paid cloud API dependencies, the system enforces a hard budget ceiling of **$100/month**.

---

## 2. Infrastructure Cost Breakdown

| Category | Monthly Target | Notes |
| :--- | :--- | :--- |
| **Primary Local Server** | $0.00 | Hosted on home lab (Mac/mini server). Runs local Ollama models. |
| **Docker Pro (Optional)** | $0.00 - $11.00 | Uses Docker Personal (Free) by default. |
| **Secondary Failover VPS** | $25.00 - $60.00 | Small instance (e.g. DigitalOcean/Linode 2-4GB RAM, CPU-only). |
| **Cloudflare Tunnel / Zero Trust**| $0.00 | Cloudflare Free tier for secure tunneling. |
| **Encrypted Storage Backups** | $5.00 - $15.00 | Offsite backups/snapshots (e.g. B2, Wasabi, or AWS S3). |
| **Uptime Monitoring** | $0.00 - $10.00 | Heartbeat checkers and webhook alerts. |
| **Total Estimated Cost** | **$30.00 - $96.00 / month** | Stays safely under the $100 cap. |

---

## 3. Concurrency Limits for Resource Protection
To avoid server memory exhaustion or rate-limiting bans on low-cost infrastructure, the Swarm enforces strict limits:
- `registered_agents`: **300** (max identities)
- `active_agent_limit`: **20** (max parallel execution)
- `llm_concurrency_limit`: **3**
- `browser_concurrency_limit`: **2** (Playwright sessions)
- `qa_worker_limit`: **4**
- `code_worker_limit`: **4**
