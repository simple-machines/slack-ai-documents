#!/bin/bash
set -e

# Function to print in color
print_status() {
    local color=$1
    local message=$2
    echo -e "\e[${color}m${message}\e[0m"
}

# Ensure environment variables are set
if [ -z "$PROJECT_ID" ]; then
    print_status "31" "Error: PROJECT_ID environment variable is not set"
    exit 1
fi

if [ -z "$LOCATION" ]; then
    print_status "31" "Error: LOCATION environment variable is not set"
    exit 1
fi

# Check for service account key
if [ ! -f "service-account-key.json" ]; then
    print_status "31" "Error: service-account-key.json not found"
    exit 1
fi

print_status "34" "Building container..."
# Build for linux/amd64 platform explicitly
docker build --platform linux/amd64 -t vector-search .

# Tag for Artifact Registry
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search:latest"
docker tag vector-search $IMAGE_NAME

print_status "34" "Pushing to Artifact Registry..."
docker push $IMAGE_NAME

print_status "34" "Deploying to Cloud Run..."
gcloud run deploy vector-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=1 \
  --port=8080 \
  --service-account=vector-search-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME},SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}"

# Check deployment status
if [ $? -eq 0 ]; then
    print_status "32" "Deployment successful!"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe vector-search --platform managed --region $LOCATION --format 'value(status.url)')
    print_status "32" "Service URL: $SERVICE_URL"
else
    print_status "31" "Deployment failed!"
    
    # Get and display logs
    print_status "33" "Fetching logs..."
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vector-search" --limit 50
fi