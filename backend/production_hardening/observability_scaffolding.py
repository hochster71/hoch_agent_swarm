# Observability metrics and structured JSON logging
import json
import logging
import time
from typing import Dict, Any

class JsonStructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "thread": record.threadName
        }
        if hasattr(record, "trace_id"):
            log_payload["trace_id"] = record.trace_id
        return json.dumps(log_payload)

class PrometheusMetricsExporter:
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "http_requests_total": 0,
            "mutation_gate_denials": 0,
            "session_active_count": 0
        }

    def record_request(self):
        self.metrics["http_requests_total"] += 1

    def record_denial(self):
        self.metrics["mutation_gate_denials"] += 1

    def get_metrics_payload(self) -> str:
        lines = []
        for key, val in self.metrics.items():
            lines.append(f"# HELP {key} System metric count")
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {val}")
        return "\n".join(lines)
