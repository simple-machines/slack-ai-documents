<!-- # create and configure gcs bucket
gsutil mb -l us-central1 gs://slack-ai-vector-search -->

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