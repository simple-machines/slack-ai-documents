# src/config/config.py

import os

# Google Cloud settings
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini model settings
GEMINI_MODEL = "gemini-1.5-flash"
MAX_OUTPUT_TOKENS = 2048
TEMPERATURE = 0.2

# Storage paths
DOCUMENTS_PREFIX = "documents/"

# Search settings
TOP_K = 5

# API settings
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Slack settings
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_MAX_RESULTS = 5
SLACK_RESULT_CHUNK_SIZE = 300
SLACK_RATE_LIMIT = 20
