#!/bin/bash
set -e

# ensure environment variables are set
if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID environment variable is not set"
    exit 1
fi

if [ -z "$LOCATION" ]; then
    echo "Error: LOCATION environment variable is not set"
    exit 1
fi

# build the container
docker build -t vector-search .

# tag for artifact registry
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/vector-search/vector-search:latest"
docker tag vector-search $IMAGE_NAME

# push to artifact registry
docker push $IMAGE_NAME

# deploy to cloud run
gcloud run deploy vector-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --min-instances=1 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME}"