# Gemini Document Search with Slack Integration

A document search service that uses Google's Gemini API to enable natural language search through documents via Slack. Built with FastAPI and Google Cloud Platform services.

## Overview

This service allows users to:
- Upload documents via API endpoints
- Search through documents using natural language via Slack commands
- Get relevant passages with explanations and context
- Process multiple document types including PDFs, code files, and text documents

## Prerequisites

- Google Cloud Platform account
- Slack workspace with admin access
- Python 3.9+
- `gcloud` CLI installed
- Docker installed

## Setup Instructions

### 1. Google Cloud Setup

First, set up your Google Cloud environment:

```bash
# Create and configure GCS bucket
gsutil mb -l us-central1 gs://slack-ai-document-search

# Set environment variables
export PROJECT_ID=semantcai
export LOCATION=us-central1
export BUCKET_NAME=slack-ai-document-search
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_SIGNING_SECRET=your-signing-secret
export GEMINI_API_KEY=your-gemini-api-key

# Create service account and configure permissions
gcloud iam service-accounts create document-search-sa

gcloud projects add-iam-policy-binding semantcai \
    --member="serviceAccount:document-search-sa@semantcai.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding semantcai \
    --member="serviceAccount:document-search-sa@semantcai.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Download service account key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=document-search-sa@semantcai.iam.gserviceaccount.com
```

### 2. Slack App Configuration

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Name your app and select your workspace

#### Basic Information Setup:
- Under "Basic Information":
  - Note your "Signing Secret" (needed for SLACK_SIGNING_SECRET)
  - In "Display Information", add app name and description

#### Bot Token Scopes:
Under "OAuth & Permissions":
1. Add these Bot Token Scopes:
   - `app_mentions:read`
   - `chat:write`
   - `commands`
2. Install app to workspace
3. Copy "Bot User OAuth Token" (needed for SLACK_BOT_TOKEN)

#### Slash Commands:
Under "Slash Commands":
1. Click "Create New Command"
2. Configure the `/find` command:
   ```
   Command: /find
   Request URL: https://your-app-url/slack/commands
   Short Description: Search through documents
   Usage Hint: [search query]
   ```

#### Event Subscriptions:
Under "Event Subscriptions":
1. Enable Events
2. Set Request URL to: `https://your-app-url/slack/events`
3. Subscribe to bot events:
   - `app_mention`
4. Save Changes

### 3. Local Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/gemini-document-search.git
cd gemini-document-search

# Install dependencies
pip install -r requirements.txt

# Set up environment variables in .env file
cp .env.example .env
# Edit .env with your values
```

### 4. Deployment

```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Deploy to Cloud Run
./scripts/deploy.sh
```

## Project Structure

```
src/
├── api/
│   ├── app.py          # FastAPI application
│   ├── routes.py       # API endpoints
│   └── slack_handler.py # Slack integration
├── processor/
│   └── gemini_processor.py # Document processing
├── search/
│   └── gemini_searcher.py  # Search implementation
├── storage/
│   └── gcs.py         # Google Cloud Storage handler
└── utils/
    └── slack_utils.py  # Slack utilities
```

## Key Components

### Document Processing (`src/processor/gemini_processor.py`)
- Handles document uploads
- Processes documents using Gemini API
- Extracts content and metadata
- Stores results in GCS

### Search Implementation (`src/search/gemini_searcher.py`)
- Implements semantic search using Gemini
- Scores and ranks results
- Filters by relevance threshold (>= 0.90)
- Returns complete passages with context

### Slack Integration (`src/api/slack_handler.py`)
- Handles slash commands and mentions
- Processes search queries
- Formats and sends responses
- Manages asynchronous searches

## Usage

### Slack Commands

1. Basic search:
```
/find what is our travel policy?
```

2. Mention the bot:
```
@YourBot what are our security guidelines?
```

### API Endpoints

1. Upload document:
```bash
curl -X POST "https://your-app-url/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

2. Search documents:
```bash
curl -X POST "https://your-app-url/find" \
  -H "Content-Type: application/json" \
  -d '{"query": "what is our policy on remote work?"}'
```

## Configuration

Key configuration settings in `src/config/config.py`:
- `TOP_P_THRESHOLD`: Cumulative relevance score threshold (2.0)
- `SLACK_MAX_RESULTS`: Maximum results to show (10)
- `GEMINI_MODEL`: Model version ("gemini-1.5-flash")

## Troubleshooting

1. Slack Authentication Issues:
   - Verify SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
   - Check bot permissions
   - Verify event subscription URL

2. Document Processing Issues:
   - Check file format support
   - Verify GCS permissions
   - Check service account key

3. Search Issues:
   - Verify document upload success
   - Check Gemini API key
   - Review search query format

## License

[MIT License](LICENSE)

## Support

For support:
1. Check documentation
2. Review troubleshooting guide
3. Open GitHub issue
4. Contact maintainers