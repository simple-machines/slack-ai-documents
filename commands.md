```
export PROJECT_ID=semantc-ai
export LOCATION=us-central1
export BUCKET_NAME=slack-ai-vector-search
export SLACK_BOT_TOKEN=xoxb-
export SLACK_SIGNING_SECRET=
```

# create and configure gcs bucket
gsutil mb -l us-central1 gs://slack-ai-vector-search

# create service account and download key
```
gcloud iam service-accounts create vector-search-sa

gcloud projects add-iam-policy-binding semantc-ai \
    --member="serviceAccount:vector-search-sa@semantc-ai.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding semantc-ai \
    --member="serviceAccount:vector-search-sa@semantc-ai.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=vector-search-sa@semantc-ai.iam.gserviceaccount.com
```

# run processing script
python scripts/process_documents.py --input-dir ./documents


# run everything locally using Docker:
```
docker-compose up --build
```
```
docker-compose run --rm vector-search python scripts/process_documents.py --input-dir /app/documents
```

```
http://localhost:8080/docs#/default/upload_document_documents__post
```

# build and deploy to Cloud Run
chmod +x scripts/deploy.sh

./scripts/deploy.sh

```
source .env
./scripts/deploy.sh
```


### TEST LOCALLY!
# make sure your service-account-key.json is in your project root
docker build -t vector-search .

# Run with service account mounted
docker run -p 8080:8080 \
  -e PROJECT_ID=${PROJECT_ID} \
  -e BUCKET_NAME=${BUCKET_NAME} \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa-key.json \
  -v ${PWD}/service-account-key.json:/tmp/keys/sa-key.json:ro \
  vector-search