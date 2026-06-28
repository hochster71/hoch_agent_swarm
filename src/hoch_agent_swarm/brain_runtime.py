# -*- coding: utf-8 -*-
"""
brain_runtime.py — Central Evidence Ingestion, Vector Index, and Knowledge Graph Runtime.
"""

from __future__ import annotations
import os
import json
import sqlite3
import re
import math
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# Project root resolution
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent
DB_DIR = PROJECT_ROOT / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "brain_evidence.db"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# Simple common stop words to improve TF-IDF indexing relevance
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "of", "in", 
    "for", "on", "with", "as", "at", "by", "an", "it", "this", "that", "from", "be", "has"
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric words, ignoring stop words."""
    words = re.findall(r"\b\w{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


class BrainRuntime:
    def __init__(self):
        self.db_path = DB_PATH
        self.conn: Optional[sqlite3.Connection] = None
        self.initialize_db()

    def initialize_db(self):
        """Creates SQLite tables if they do not exist."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Evidence nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_nodes (
                id TEXT PRIMARY KEY,
                path TEXT,
                chunk_index INTEGER,
                content TEXT,
                trust_score REAL,
                timestamp TEXT,
                commit_sha TEXT,
                author TEXT,
                metadata TEXT
            )
        """)
        
        # Knowledge Graph edges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                from_node TEXT,
                to_node TEXT,
                relationship_type TEXT,
                PRIMARY KEY (from_node, to_node, relationship_type)
            )
        """)
        
        self.conn.commit()

    def ingest_artifacts(self) -> Dict[str, Any]:
        """Crawls artifacts directory, chunks markdown/JSON, logs git signatures, computes trust."""
        if not ARTIFACTS_DIR.exists():
            return {"status": "ERROR", "message": f"Artifacts folder not found: {ARTIFACTS_DIR}"}

        cursor = self.conn.cursor()
        ingested_count = 0
        file_count = 0

        # Scan artifacts folder
        for root, _, files in os.walk(str(ARTIFACTS_DIR)):
            for file in files:
                file_path = Path(root) / file
                # Skip temporary, scratch, and binary files
                if file_path.suffix not in [".md", ".json"] or ".db" in file_path.name:
                    continue
                if "scratch" in file_path.parts or ".system_generated" in file_path.parts:
                    continue

                file_count += 1
                rel_path = file_path.relative_to(PROJECT_ROOT).as_posix()
                content = ""
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                # Fetch Git details if possible
                git_sha = "local-draft"
                git_date = datetime.now(timezone.utc).isoformat()
                git_author = "local-agent"
                try:
                    res = subprocess.run(
                        ["git", "log", "-n", "1", "--pretty=format:%H|%cI|%an", "--", str(file_path)],
                        capture_output=True, text=True, check=False, cwd=str(PROJECT_ROOT)
                    )
                    if res.returncode == 0 and res.stdout:
                        parts = res.stdout.strip().split("|")
                        if len(parts) >= 3:
                            git_sha, git_date, git_author = parts[0], parts[1], parts[2]
                except Exception:
                    pass

                # Ingest based on file type
                if file_path.suffix == ".md":
                    # Chunk by headings (Markdown sections)
                    sections = self._chunk_markdown(content)
                    for idx, (heading, body) in enumerate(sections):
                        chunk_id = f"{rel_path}#chunk-{idx}"
                        full_content = f"[{heading}]\n{body}" if heading else body
                        trust = self._calculate_trust_score(rel_path, full_content, git_sha != "local-draft")
                        
                        meta = json.dumps({
                            "heading": heading,
                            "file_name": file_path.name
                        })
                        
                        cursor.execute("""
                            INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                content=excluded.content,
                                trust_score=excluded.trust_score,
                                timestamp=excluded.timestamp,
                                commit_sha=excluded.commit_sha,
                                author=excluded.author,
                                metadata=excluded.metadata
                        """, (chunk_id, rel_path, idx, full_content, trust, git_date, git_sha, git_author, meta))
                        ingested_count += 1

                elif file_path.suffix == ".json":
                    # Handle JSON files
                    try:
                        data = json.loads(content)
                        # Custom parsing for PromptQA files to chunk by prompt ID
                        if "promptqa/" in rel_path.lower() and isinstance(data, dict) and file_path.name != "routing_eval_results.json":
                            for p_id, value in data.items():
                                chunk_id = f"{rel_path}#prompt-{p_id}"
                                body = json.dumps({p_id: value}, indent=2)
                                trust = self._calculate_trust_score(rel_path, body, git_sha != "local-draft")
                                meta = json.dumps({"prompt_id": p_id, "file_name": file_path.name})
                                
                                cursor.execute("""
                                    INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(id) DO UPDATE SET
                                        content=excluded.content,
                                        trust_score=excluded.trust_score,
                                        timestamp=excluded.timestamp,
                                        commit_sha=excluded.commit_sha,
                                        author=excluded.author,
                                        metadata=excluded.metadata
                                """, (chunk_id, rel_path, 0, body, trust, git_date, git_sha, git_author, meta))
                                ingested_count += 1
                        # If list of records
                        elif isinstance(data, list):
                            for idx, record in enumerate(data):
                                if isinstance(record, dict) and "id" in record:
                                    chunk_id = f"{rel_path}#rec-{record['id']}"
                                    body = json.dumps(record, indent=2)
                                    trust = self._calculate_trust_score(rel_path, body, git_sha != "local-draft")
                                    meta = json.dumps({"record_id": record["id"], "file_name": file_path.name})
                                    
                                    cursor.execute("""
                                        INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ON CONFLICT(id) DO UPDATE SET
                                            content=excluded.content,
                                            trust_score=excluded.trust_score,
                                            timestamp=excluded.timestamp,
                                            commit_sha=excluded.commit_sha,
                                            author=excluded.author,
                                            metadata=excluded.metadata
                                    """, (chunk_id, rel_path, idx, body, trust, git_date, git_sha, git_author, meta))
                                    ingested_count += 1
                        else:
                            chunk_id = f"{rel_path}#full"
                            trust = self._calculate_trust_score(rel_path, content, git_sha != "local-draft")
                            meta = json.dumps({"file_name": file_path.name})
                            cursor.execute("""
                                INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(id) DO UPDATE SET
                                    content=excluded.content,
                                    trust_score=excluded.trust_score,
                                    timestamp=excluded.timestamp,
                                    commit_sha=excluded.commit_sha,
                                    author=excluded.author,
                                    metadata=excluded.metadata
                            """, (chunk_id, rel_path, 0, content, trust, git_date, git_sha, git_author, meta))
                            ingested_count += 1
                    except Exception:
                        pass

        self.conn.commit()
        
        # Post-ingestion: populate knowledge graph edges dynamically
        self._build_graph_edges()

        return {
            "status": "SUCCESS",
            "total_files_scanned": file_count,
            "total_chunks_ingested": ingested_count,
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }

    def query_evidence(self, query: str, limit: int = 5, min_trust: float = 0.0) -> List[Dict[str, Any]]:
        """Calculates TF-IDF on ingested chunks and returns cosine-similarity ranked results."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, path, content, trust_score, timestamp, commit_sha, author, metadata FROM evidence_nodes WHERE trust_score >= ?", (min_trust,))
        rows = cursor.fetchall()
        
        if not rows:
            return []

        # Tokenize all documents
        docs = []
        doc_tokens = []
        for r in rows:
            doc_id = r["id"]
            content = r["content"]
            tokens = tokenize(content)
            docs.append(dict(r))
            doc_tokens.append(tokens)

        # Compute document frequencies (DF) for IDF calculation
        df = {}
        for tokens in doc_tokens:
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        total_docs = len(docs)
        
        # IDF helper
        def get_idf(term: str) -> float:
            count = df.get(term, 0)
            if count == 0:
                return 0.0
            return math.log(1.0 + (total_docs / count))

        # Query TF-IDF vector
        query_words = tokenize(query)
        if not query_words:
            # Fallback to trust score / recency if query yields no tokens
            return sorted(docs, key=lambda x: (x["trust_score"], x["timestamp"]), reverse=True)[:limit]

        query_tf = {}
        for qw in query_words:
            query_tf[qw] = query_tf.get(qw, 0) + 1

        query_vector = {}
        query_norm = 0.0
        for qw, tf in query_tf.items():
            idf = get_idf(qw)
            tfidf = tf * idf
            query_vector[qw] = tfidf
            query_norm += tfidf ** 2
        query_norm = math.sqrt(query_norm)

        # Match docs
        results = []
        for idx, doc in enumerate(docs):
            tokens = doc_tokens[idx]
            if not tokens:
                continue

            # Doc TF
            doc_tf = {}
            for t in tokens:
                doc_tf[t] = doc_tf.get(t, 0) + 1

            # Doc vector
            doc_vector = {}
            doc_norm = 0.0
            for t, tf in doc_tf.items():
                idf = get_idf(t)
                tfidf = tf * idf
                doc_vector[t] = tfidf
                doc_norm += tfidf ** 2
            doc_norm = math.sqrt(doc_norm)

            # Cosine similarity dot product
            dot_product = 0.0
            for qw, q_val in query_vector.items():
                if qw in doc_vector:
                    dot_product += q_val * doc_vector[qw]

            similarity = 0.0
            if query_norm > 0 and doc_norm > 0:
                similarity = dot_product / (query_norm * doc_norm)

            # Inject score and formatting
            doc["relevance_score"] = round(similarity, 4)
            # Add basic snippet preview
            doc["snippet"] = self._create_snippet(doc["content"], query_words)
            
            if similarity > 0:
                results.append(doc)

        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    def get_knowledge_graph(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns all graph nodes and edges for knowledge mapping."""
        cursor = self.conn.cursor()
        
        # Fetch nodes
        cursor.execute("SELECT id, path, trust_score, timestamp, metadata FROM evidence_nodes")
        nodes_rows = cursor.fetchall()
        nodes = []
        for nr in nodes_rows:
            meta = {}
            try:
                meta = json.loads(nr["metadata"] or "{}")
            except Exception:
                pass
            nodes.append({
                "id": nr["id"],
                "type": "evidence",
                "label": meta.get("heading") or nr["path"].split("/")[-1],
                "trust_score": nr["trust_score"],
                "path": nr["path"]
            })

        # Fetch edges
        cursor.execute("SELECT from_node, to_node, relationship_type FROM graph_edges")
        edges_rows = cursor.fetchall()
        edges = [dict(er) for er in edges_rows]

        return {"nodes": nodes, "edges": edges}

    def validate_gap_closures(self) -> Dict[str, Any]:
        """Cross-checks open promptbrain gaps against ingested evidence nodes to see if requirements are met."""
        # 1. Load open gaps
        from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
        pm = get_promptbrain_manager()
        
        gaps_list = pm.gaps
        if not gaps_list:
            return {"status": "SUCCESS", "message": "No prompt gaps found.", "closures": []}

        # Load PromptQA scores & regression if available
        qa_scores = {}
        qa_regression = {}
        try:
            from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
            qa = get_promptqa_manager()
            qa_scores = qa.scores
            qa_regression = qa.regression_results
        except Exception:
            pass

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, path, content, trust_score FROM evidence_nodes")
        nodes = cursor.fetchall()

        closures = []
        closed_count = 0

        for gap in gaps_list:
            gap_id = gap["missing_prompt_id"]
            gap_title = gap["missing_title"]
            
            # Check promptqa release-grade and regression pass status
            matching_prompt = next((p for p in pm.revised_prompts if p["id"] == gap_id), None)
            is_critical = gap_id.startswith('BRAIN-') or gap_id.startswith('PROMPT-') or gap_id.startswith('GAP-') or gap_id.startswith('SWARM-') or gap_id.startswith('GOVFRAME-')
            threshold = 90.0 if is_critical else 85.0
            
            qa_score = qa_scores.get(gap_id, {}).get("overall_score", 0.0)
            regression_pass = qa_regression.get(gap_id, {}).get("regression_pass", False)
            
            is_fully_validated = (matching_prompt is not None) and (qa_score >= threshold) and regression_pass

            # Search evidence nodes for mention of gap ID or title keyword (fallback/corroboration)
            matching_nodes = []
            for node in nodes:
                content_lower = node["content"].lower()
                if gap_id.lower() in content_lower or gap_title.lower() in content_lower:
                    is_closed = "decision: pass" in content_lower or "verdict: pass" in content_lower
                    matching_nodes.append({
                        "node_id": node["id"],
                        "path": node["path"],
                        "trust_score": node["trust_score"],
                        "resolves": is_closed
                    })

            # Determine overall status
            status = "OPEN"
            resolved_by = None
            
            if is_fully_validated:
                status = "RESOLVED"
                resolved_by = f"artifacts/promptqa/prompt_quality_scores.json#prompt-{gap_id}"
                closed_count += 1
            else:
                for match in matching_nodes:
                    if match["resolves"] and match["trust_score"] >= 80:
                        status = "RESOLVED"
                        resolved_by = match["node_id"]
                        closed_count += 1
                        break

            closures.append({
                "gap_id": gap["gap_id"],
                "missing_prompt_id": gap_id,
                "missing_title": gap_title,
                "status": status,
                "matching_evidence_nodes": matching_nodes,
                "resolved_by_node": resolved_by
            })

        return {
            "status": "AUDITED",
            "total_gaps": len(gaps_list),
            "closed_gaps": closed_count,
            "open_gaps": len(gaps_list) - closed_count,
            "closures": closures
        }

    # --- Private Helpers ---
    def _chunk_markdown(self, text: str) -> List[Tuple[str, str]]:
        """Splits markdown file content by headers, returning lists of (heading_text, section_body)."""
        sections = []
        current_heading = ""
        current_body = []
        
        lines = text.splitlines()
        for line in lines:
            if line.startswith("#"):
                # Save previous section if not empty
                if current_body or current_heading:
                    sections.append((current_heading, "\n".join(current_body).strip()))
                current_heading = line.lstrip("#").strip()
                current_body = []
            else:
                current_body.append(line)
                
        # Save last section
        if current_body or current_heading:
            sections.append((current_heading, "\n".join(current_body).strip()))

        # Fallback if no headings found
        if not sections:
            sections.append(("", text.strip()))
            
        return sections

    def _calculate_trust_score(self, path: str, content: str, has_git: bool) -> float:
        """Calculates 0-100 score representing evidence provenance trust."""
        score = 70.0
        
        # Git signature present boost
        if has_git:
            score += 10.0
            
        # Canonical artifact boost
        name_lower = path.lower()
        if "security_audit" in name_lower or "release_packet" in name_lower:
            score += 15.0
        elif "execution_plan" in name_lower or "asset_map" in name_lower:
            score += 10.0

        # Verification keywords presence
        if "facts observed" in content.lower():
            score += 5.0

        return min(score, 100.0)

    def _create_snippet(self, content: str, query_words: List[str]) -> str:
        """Extracts a matching snippet around query words for display."""
        # Find first matching query word location
        text_lower = content.lower()
        idx = -1
        for qw in query_words:
            idx = text_lower.find(qw)
            if idx != -1:
                break
        
        if idx == -1:
            return content[:150] + "..." if len(content) > 150 else content

        start = max(0, idx - 60)
        end = min(len(content), idx + 120)
        
        snippet = content[start:end]
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        return prefix + snippet.strip().replace("\n", " ") + suffix

    def _build_graph_edges(self):
        """Dynamically creates links between evidence nodes and prompts/targets."""
        cursor = self.conn.cursor()
        
        # Retrieve all nodes
        cursor.execute("SELECT id, path, content, metadata FROM evidence_nodes")
        nodes = cursor.fetchall()
        
        edges = []
        for node in nodes:
            node_id = node["id"]
            content = node["content"].lower()
            
            meta = {}
            try:
                meta = json.loads(node["metadata"] or "{}")
            except Exception:
                pass
                
            # If this is a PromptQA node keyed by prompt_id, link it!
            if "prompt_id" in meta:
                p_id = meta["prompt_id"].upper()
                edges.append((node_id, f"prompt-{p_id}", "qa_evidence_for"))
            
            # Edge: cites specific framework or prompt ID
            # Search for prompt ID pattern like "BRAIN-001" or "CODE-001"
            prompt_matches = re.findall(r"\b[a-z]+-\d{3}\b", content)
            for pm in prompt_matches:
                edges.append((node_id, f"prompt-{pm.upper()}", "references_prompt"))

            # Check framework associations
            if "800-53" in content:
                edges.append((node_id, "framework-nist-800-53", "applies_to_control"))
            if "cmmc" in content:
                edges.append((node_id, "framework-cmmc", "applies_to_control"))
            if "zero trust" in content:
                edges.append((node_id, "framework-zero-trust", "applies_to_control"))

            # Path-based relationships (CyberGov & ConMon)
            if "cybergov" in node["path"].lower():
                edges.append((node_id, "framework-nist-800-53", "gov_security_guidance"))
            if "conmon" in node["path"].lower():
                edges.append((node_id, "framework-nist-800-53", "continuous_monitoring_finding"))

        # Save to database
        for edge in edges:
            cursor.execute("""
                INSERT OR IGNORE INTO graph_edges (from_node, to_node, relationship_type)
                VALUES (?, ?, ?)
            """, edge)
        self.conn.commit()


# Singleton runtime instance
_runtime_instance = None

def get_brain_runtime() -> BrainRuntime:
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = BrainRuntime()
    return _runtime_instance
