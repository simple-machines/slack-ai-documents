#!/bin/bash

# scripts/deploy.sh

set -e

# build the container
docker build -t vector-search .

# tag for Google Container Registry
IMAGE_NAME="gcr.io/$PROJECT_ID/vector-search:latest"
docker tag vector-search $IMAGE_NAME

# push to Container Registry
docker push $IMAGE_NAME

# deploy to Cloud Run
gcloud run deploy vector-search \
  --image $IMAGE_NAME \
  --platform managed \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory=4Gi \
  --min-instances=1 \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME"
