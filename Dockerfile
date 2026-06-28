FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project specification files
COPY pyproject.toml uv.lock ./

# Install dependencies (cached step)
RUN uv sync --frozen --no-install-project

# Copy remaining repository source code
COPY . .

# Install the project itself in editable mode
RUN uv sync --frozen

# Expose app port
EXPOSE 8086

# Set PYTHONPATH and SWARM_UI_PORT environment variables
ENV PYTHONPATH="/app/src:/app"
ENV SWARM_UI_PORT="8086"

# Default command starts the operator cockpit launcher
CMD ["uv", "run", "operator_launch"]
