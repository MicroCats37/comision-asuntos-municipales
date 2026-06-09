FROM python:3.10-slim

# Install uv and gosu
RUN pip install --no-cache-dir uv && \
    apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gosu \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy dependency files first (for caching layer)
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

# Install Python dependencies using uv
RUN uv sync --frozen --no-install-project

# Copy project source into /app (which is the workdir)
COPY backend/ .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python manage.py check --settings=config.settings || exit 1

# Default command via entrypoint
CMD ["/app/docker/entrypoint.sh"]
