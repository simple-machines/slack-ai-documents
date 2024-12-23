FROM python:3.9-slim

WORKDIR /app

# install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# create directory for service account key
RUN mkdir -p /tmp/keys

# copy requirements and setup files first
COPY requirements.txt setup.py ./

# install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# copy application code
COPY . .

# use environment variable for port
ENV PORT=8080
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa-key.json

EXPOSE 8080

# use Python to run uvicorn
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]