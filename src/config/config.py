# src/config/config.py

import os

# Google Settings
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Drive Settings
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/service-account-key.json")

# Gemini Model Settings
GEMINI_MODEL = "gemini-1.5-flash" # "gemini-1.5-pro-latest"  # "gemini-1.5-flash"
MAX_OUTPUT_TOKENS = 2048
TEMPERATURE = 0.2

# Search Settings
TOP_P_THRESHOLD = 2.0

# API Settings
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Slack Settings
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_MAX_RESULTS = 5
SLACK_RESULT_CHUNK_SIZE = 1000
SLACK_RATE_LIMIT = 20