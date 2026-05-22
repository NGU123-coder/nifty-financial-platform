# --- BUILD STAGE ---
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --prefix=/install -r requirements.txt

# --- FINAL STAGE ---
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/web_api" \
    PATH="/home/appuser/.local/bin:$PATH"

# Create a non-root user
RUN useradd -m appuser
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy project
COPY --chown=appuser:appuser . .

# Ensure scripts are executable
RUN chmod +x /app/web_api/manage.py

# Collect static files
RUN python web_api/manage.py collectstatic --noinput

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000
