# Multi-stage Dockerfile for Publer MCP following Spinnable MCP Playbook
# Stage 1: Build stage with uv for dependency management
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy uv.lock and pyproject.toml for dependency installation
COPY uv.lock pyproject.toml ./

# Install dependencies using uv with frozen lockfile for reproducible builds
RUN uv sync --frozen --no-dev

# Stage 2: Production runtime
FROM python:3.12-alpine AS runtime

# Install system dependencies and create non-root user
RUN apk add --no-cache \
    curl \
    && addgroup -g 1001 mcpuser \
    && adduser -D -u 1001 -G mcpuser mcpuser

# Set working directory  
WORKDIR /app

# Copy Python environment from builder stage
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv

# Copy application code
COPY --chown=mcpuser:mcpuser publer_mcp/ /app/publer_mcp/
COPY --chown=mcpuser:mcpuser pyproject.toml /app/

# Add .venv to PATH for Python execution
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user for security
USER mcpuser

# Expose the application port
EXPOSE 3000

# Health check endpoint for monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Start the Publer MCP server
CMD ["python", "-m", "publer_mcp.server"]