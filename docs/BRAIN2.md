# BRAIN2 — Central Evidence Ingestion, Vector Index, and Knowledge Graph Runtime

The Evidence Brain runtime (BRAIN2) is the operational data, search, and validation engine for the HOCH Agent Swarm. It ingests repository artifacts dynamically, indexes them for vector-approx TF-IDF search, tracks git provenance signatures, scores evidence trust levels, maps semantic connections in a knowledge graph, and validates POA&M gap closures.

## Compliance Notice & Status Boundary

> [!IMPORTANT]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> 
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated, and no claim of absolute security is made.*

## Database Schema & Core Tables

The system persists evidence in a local SQLite database at `data/brain_evidence.db` containing the following tables:

### 1. `evidence_nodes`
Stores ingested document sections and JSON record chunks.
- `id` (TEXT PRIMARY KEY): Unique identifier (e.g., `artifacts/research/asset_map.md#chunk-0`).
- `path` (TEXT): File path relative to project root.
- `chunk_index` (INTEGER): Index of the chunk within the source file.
- `content` (TEXT): Chunk content body.
- `trust_score` (REAL): Provenance score (0.0 to 100.0).
- `timestamp` (TEXT): ISO time of last modification (extracted from Git).
- `commit_sha` (TEXT): Git commit hash (or `local-draft`).
- `author` (TEXT): Git author name (or `local-agent`).
- `metadata` (TEXT): JSON string of chunk metadata.

### 2. `graph_edges`
Stores relationship edges within the knowledge graph.
- `from_node` (TEXT): ID of source evidence node.
- `to_node` (TEXT): ID of target node (e.g. `prompt-GOVFRAME-001`, `framework-nist-800-53`).
- `relationship_type` (TEXT): Type of connection (`references_prompt`, `applies_to_control`).

---

## Technical Mechanisms

### 1. Dynamic Ingestion & Chunking
- **Markdown Parser**: Chunked by headings (`#`, `##`, `###`) to group text semantically. If no headings are present, the file is ingested as a single chunk.
- **JSON Parser**: If a JSON file contains a list of objects, it indexes individual dictionary entries by ID. Otherwise, it ingests the full JSON string.
- **Git Metadata Extraction**: Uses a fast subprocess command `git log -n 1 --pretty=format:"%H|%cI|%an" -- <path>` to extract the commit hash, modification timestamp, and author signature.

### 2. Local TF-IDF Vector Search Index
Since external LLM API dependencies are prohibited, retrieval is approximated locally:
- Alphanumeric strings are parsed into lowercase token vectors, excluding common grammatical stop words.
- In-memory Inverse Document Frequency (IDF) is calculated across all nodes:
  $$\text{IDF}(t) = \ln\left(1.0 + \frac{N}{\text{DF}(t)}\right)$$
- Term Frequency (TF) weights vectors for Cosine Similarity:
  $$\text{CosineSimilarity}(Q, D) = \frac{Q \cdot D}{\|Q\| \|D\|}$$

### 3. Source Trust Scoring Engine
A base trust score of `70.0` is adjusted by these criteria:
- **Git Signature present**: $+10.0$ points
- **Canonical security/release reports** (e.g. `security_audit_report.md`, `release_packet.md`): $+15.0$ points
- **Durable execution/asset maps**: $+10.0$ points
- **Validation markers present** (`"facts observed"`): $+5.0$ points
- **Max Score**: Cap at $100.0$.

### 4. Gap Closure Auditor
Queries open prompt gaps and searches the evidence index for matching gap IDs or keywords. A gap status shifts to `RESOLVED` if:
1. An evidence node contains matching keywords.
2. The node content explicitly indicates a successful audit (`"decision: pass"` or `"verdict: pass"`).
3. The node's trust score is $\ge 80.0$.

---

## API Endpoints

- `POST /api/v1/brain/ingest`: Triggers crawl, parsing, and SQLite population. Returns ingestion stats.
- `GET /api/v1/brain/query`: Search index with optional `min_trust` query filters.
- `GET /api/v1/brain/graph`: Returns nodes and edges list for visualization.
- `GET /api/v1/brain/citations?node_id=<id>`: Retrieves raw content and chain-of-custody signatures.
- `GET /api/v1/brain/validation-status`: Lists POA&M gap validation status.
