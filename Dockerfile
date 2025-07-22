# Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml for dependency installation
COPY pyproject.toml .

# Create a basic uv.lock file (since we don't have one yet)
RUN uv lock

# Install Python dependencies using uv
RUN uv sync

# Copy application code
COPY grafana-mcp-server/src ./src

# Create a non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Expose the port
EXPOSE 8000

# Set PYTHONPATH and run as a module
ENV PYTHONPATH=/app
ENTRYPOINT ["uv", "run", "-m", "src.grafana_mcp_server.mcp_server"]
