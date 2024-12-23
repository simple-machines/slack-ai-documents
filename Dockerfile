FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create directory for service account key
RUN mkdir -p /tmp/keys

# Copy requirements and setup files first
COPY requirements.txt setup.py ./

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# Copy application code
COPY . .

# Use environment variable for port
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa-key.json

EXPOSE ${PORT}

# Use Python to run uvicorn directly
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]