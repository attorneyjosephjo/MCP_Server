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

# Expose port for HTTP transport
EXPOSE 3000

# Health check - use wget or curl for better reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/health').read()" || exit 1

# Run the server in HTTP mode
CMD ["uv", "run", "legal_rag_server.py", "--http"]
