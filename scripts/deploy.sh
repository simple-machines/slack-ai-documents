#!/bin/bash
set -e

# Ensure environment variables are set
if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID environment variable is not set"
  exit 1
fi

if [ -z "$LOCATION" ]; then
  echo "Error: LOCATION environment variable is not set"
  exit 1
fi

# Create a buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "cloudrun-builder"; then
    docker buildx create --name cloudrun-builder --use
fi

docker buildx use cloudrun-builder

# Build images for both architectures, tagging them with arch-specific tags
ARCH_AMD64_IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search-amd64:latest"
ARCH_ARM64_IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search-arm64:latest"

docker buildx build --platform linux/amd64 -t $ARCH_AMD64_IMAGE --push .
docker buildx build --platform linux/arm64 -t $ARCH_ARM64_IMAGE --push .

# Create a manifest list for the final image
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search:latest"
docker manifest create $IMAGE_NAME $ARCH_AMD64_IMAGE $ARCH_ARM64_IMAGE
docker manifest push $IMAGE_NAME

# Deploy to Cloud Run
gcloud run deploy vector-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --min-instances=1 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME}" \
  --timeout=300