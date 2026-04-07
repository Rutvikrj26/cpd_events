# Multi-stage build for CPD Events Backend
# Stage 1: Base image with system dependencies
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client library
    libpq-dev \
    # Build essentials for Python packages
    gcc \
    g++ \
    make \
    # PDF processing dependencies
    poppler-utils \
    # Image processing dependencies
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    # curl for installing uv
    curl \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Stage 2: Dependencies
FROM base AS dependencies

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies (production only, no dev dependencies)
RUN uv sync --frozen --no-dev --no-install-project

# Stage 3: Development image
FROM dependencies AS development

# Copy dependency files again for dev install
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev
RUN uv sync --frozen --no-install-project

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/mediafiles

# Expose port
EXPOSE 8000

# Run development server
CMD ["uv", "run", "python", "src/manage.py", "runserver", "0.0.0.0:8000"]

# Stage 4: Production image
FROM base AS production

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy uv from dependencies stage
COPY --from=dependencies /usr/local/bin/uv /usr/local/bin/uv

# Copy virtual environment from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/staticfiles /app/mediafiles && \
    chown -R appuser:appuser /app/staticfiles /app/mediafiles


# Copy entrypoint script
COPY --chown=appuser:appuser scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/').read()" || exit 1

# Run entrypoint
CMD ["/app/scripts/entrypoint.sh"]
