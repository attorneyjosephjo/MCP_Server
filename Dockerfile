FROM python:3.13-slim

WORKDIR /app

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application files
COPY legal_rag_server.py legal_rag_utils.py ./

# Set default port and host for HTTP transport
ENV PORT=3000
ENV HOST=0.0.0.0

# Expose port for HTTP transport
EXPOSE 3000

# Health check - check if the MCP server port is listening
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', 3000)); s.close()" || exit 1

# Run the server in HTTP mode
CMD ["uv", "run", "legal_rag_server.py", "--http"]
