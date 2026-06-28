FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project specification files and local path dependencies
COPY pyproject.toml uv.lock ./
COPY dummy_mcp/ ./dummy_mcp/

# Install dependencies (cached step)
RUN UV_CONCURRENCY=2 uv sync --frozen --no-install-project

# Copy remaining repository source code
COPY . .

# Install the project itself in editable mode
RUN UV_CONCURRENCY=2 uv sync --frozen

# Expose app port
EXPOSE 8086

# Set PYTHONPATH and SWARM_UI_PORT environment variables
ENV PYTHONPATH="/app/src:/app"
ENV SWARM_UI_PORT="8086"

# Default command starts the operator cockpit launcher
CMD ["uv", "run", "operator_launch"]
