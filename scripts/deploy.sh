#!/bin/bash
set -e

# ensure environment variables are set
if [ -z "$PROJECT_ID" ]; then
  echo "error: PROJECT_ID environment variable is not set"
  exit 1
fi

if [ -z "$LOCATION" ]; then
  echo "error: LOCATION environment variable is not set"
  exit 1
fi

if [ -z "$SLACK_BOT_TOKEN" ]; then
  echo "error: SLACK_BOT_TOKEN environment variable is not set"
  exit 1
fi

if [ -z "$SLACK_SIGNING_SECRET" ]; then
  echo "error: SLACK_SIGNING_SECRET environment variable is not set"
  exit 1
fi

if [ -z "$GOOGLE_DRIVE_FOLDER_ID" ]; then
  echo "error: GOOGLE_DRIVE_FOLDER_ID environment variable is not set"
  exit 1
fi

if [ ! -f "service-account-key.json" ]; then
  echo "error: service-account-key.json not found in project root"
  exit 1
fi

# Set working directory to project root (one level up from scripts)
cd "$(dirname "$0")/.."

# create a buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "cloudrun-builder"; then
    docker buildx create --name cloudrun-builder --use
fi

docker buildx use cloudrun-builder

# build and push AMD64 image (Cloud Run uses AMD64)
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/document-search/document-search:latest"
echo "building and pushing AMD64 image..."
docker buildx build --platform linux/amd64 \
  -t $IMAGE_NAME \
  --push \
  .

echo "deploying to Cloud Run..."
gcloud run deploy document-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=600 \
  --port=8080 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},\
LOCATION=${LOCATION},\
SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN},\
SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET},\
GEMINI_API_KEY=${GEMINI_API_KEY},\
GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID},\
GOOGLE_APPLICATION_CREDENTIALS=/service-account-key.json" \
  --service-account=document-search-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --cpu-boost \
  --execution-environment=gen2

if [ $? -eq 0 ]; then
    echo "✅ deployment successful!"
    SERVICE_URL=$(gcloud run services describe document-search --platform managed --region $LOCATION --format 'value(status.url)')
    echo "🌐 service URL: $SERVICE_URL"
    echo "testing health endpoint..."
    curl -s "${SERVICE_URL}/health"
    
    echo -e "\n📝 Next steps:"
    echo "1. Configure your Slack app with these endpoints:"
    echo "   - Events API URL: ${SERVICE_URL}/slack/events"
    echo "   - Slash Commands URL: ${SERVICE_URL}/slack/commands"
    echo "2. Subscribe to these Slack events:"
    echo "   - app_mention"
    echo "3. Add these Slack commands:"
    echo "   - /find"
    echo "4. Add these Slack bot token scopes:"
    echo "   - app_mentions:read"
    echo "   - chat:write"
    echo "   - commands"
    echo "5. Verify Google Drive folder access:"
    echo "   - Folder ID: ${GOOGLE_DRIVE_FOLDER_ID}"
    echo "   - Service account has write access to the folder"
else
    echo "❌ deployment failed!"
    echo "fetching logs..."
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=document-search" --limit 50
fi