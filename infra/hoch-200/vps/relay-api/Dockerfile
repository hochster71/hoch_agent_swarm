FROM python:3.12-slim

LABEL org.opencontainers.image.title="hoch-relay-api"
LABEL org.opencontainers.image.description="HOCH-200 relay API — Tailscale-internal only"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*


# Install dependencies
COPY relay-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY relay-api/app.py .

# Copy static dashboard assets
COPY dashboard /app/static
# Ensure the served assets are world-readable (source files may be 0600; the container
# process is non-root and otherwise cannot read them → 500s / empty responses).
RUN chmod -R a+rX /app/static

EXPOSE 3012

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3012", "--workers", "1"]
