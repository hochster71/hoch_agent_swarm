# Architectural Decision Record (ADR) — ADR-0001

## Title: Selection of SQLite for Persistence and WebSockets for Telemetry

**Document ID**: ADR-0001-RUNTIME-ARCH  
**Status**: `ACCEPTED`  
**Date**: 2026-06-25  
**Author**: System Architecture Agent  

---

## 1. Context and Problem Statement
The HOCH Swarm Console requires a secure, high-performance local data storage system to record task states, worker assignments, and cryptographically linked ledger entries. Furthermore, it must stream live telemetry (CPU, RAM, latency, execution states) to the browser dashboard at high frequencies (approx. 2000ms intervals). We must select a persistence engine and communication protocol that are local, fast, secure, and require minimal external configuration.

---

## 2. Decision
1. **Persistence Engine**: Use **SQLite** with Write-Ahead Logging (WAL) enabled as our primary database engine.
2. **Telemetry Transport**: Use **WebSockets** via FastAPI `/ws/metrics` as the data transport mechanism for real-time UI synchronization.

---

## 3. Rationale

### Why SQLite?
- **Zero Configuration**: SQLite requires no separate server setup, running entirely as an in-process file database (`swarm_ledger.db`).
- **Atomic Operations**: Supports ACID transactions, which are necessary for calculating blockchain-like SHA256 ledger block linkages securely.
- **WAL Performance**: WAL mode enables concurrent read/write access without blocking the WebSockets telemetry loops.

### Why WebSockets?
- **Low Overhead**: Unlike HTTP polling, a WebSocket connection remains open, avoiding headers overhead for high-frequency updates.
- **Bi-directional**: Allows the client to send operator actions (e.g. queue commands, overrides) and receive updates on the same connection.
- **Native Support**: FastAPI provides built-in, asynchronous WebSocket endpoints, keeping the backend code clean.

---

## 4. Consequences
- **Pros**:
  - Extremely fast response times (latency < 2ms).
  - No external Docker container or port requirements for PostgreSQL or Redis.
  - Telemetry updates instantly reflect on the dashboard.
- **Cons**:
  - SQLite is restricted to a single host (cannot scale to multi-server write-heavy systems). However, this is aligned with our target localhost sandbox design scope.
