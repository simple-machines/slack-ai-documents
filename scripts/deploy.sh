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

if [ -z "$BUCKET_NAME" ]; then
  echo "error: BUCKET_NAME environment variable is not set"
  exit 1
fi

# create a buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "cloudrun-builder"; then
    docker buildx create --name cloudrun-builder --use
fi

docker buildx use cloudrun-builder

# build and push AMD64 image (Cloud Run uses AMD64)
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search:latest"
echo "building and pushing AMD64 image..."
docker buildx build --platform linux/amd64 \
  -t $IMAGE_NAME \
  --push \
  .

echo "deploying to Cloud Run..."
gcloud run deploy vector-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --port=8080 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME},LOCATION=${LOCATION}" \
  --service-account=vector-search-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --cpu-boost \
  --execution-environment=gen2

if [ $? -eq 0 ]; then
    echo "✅ deployment successful!"
    SERVICE_URL=$(gcloud run services describe vector-search --platform managed --region $LOCATION --format 'value(status.url)')
    echo "🌐 service URL: $SERVICE_URL"
    echo "testing health endpoint..."
    curl -s "${SERVICE_URL}/health"
else
    echo "❌ deployment failed!"
    echo "fetching logs..."
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vector-search" --limit 50
fi