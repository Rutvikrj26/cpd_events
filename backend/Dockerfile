# Multi-stage build for CPD Events Backend
# Stage 1: Base image with system dependencies
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

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
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Stage 2: Dependencies
FROM base AS dependencies

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies (production only)
RUN poetry install --only main --no-root --no-directory

# Stage 3: Development image
FROM dependencies AS development

# Install development dependencies
RUN poetry install --no-root --no-directory

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/mediafiles

# Expose port
EXPOSE 8000

# Run development server
CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]

# Stage 4: Production image
FROM base AS production

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

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
