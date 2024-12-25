FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create directory for service account key and ensure /tmp is writable
RUN mkdir -p /tmp/keys && \
    chmod 777 /tmp && \
    chmod 777 /tmp/keys

# Copy requirements and setup files first
COPY requirements.txt setup.py ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# Copy application code
COPY . .

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create non-root user and set permissions
RUN useradd -m myuser && \
    chown -R myuser:myuser /app && \
    chown -R myuser:myuser /tmp

USER myuser

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--timeout-keep-alive", "75"]