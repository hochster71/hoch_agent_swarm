import uuid

def generate_otel_trace(span_name: str) -> dict:
    """Generates an OpenTelemetry compatible trace, span, and sampling context."""
    return {
        "trace_id": uuid.uuid4().hex,
        "span_id": uuid.uuid4().hex[:16],
        "sampled": True,
        "span_name": span_name
    }

def generate_correlation_id() -> str:
    return f"corr-{uuid.uuid4().hex[:12]}"
