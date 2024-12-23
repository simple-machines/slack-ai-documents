<!-- # create and configure gcs bucket
gsutil mb -l us-central1 gs://your-bucket-name-unique -->

# create service account and download key
gcloud iam service-accounts create vector-search-sa
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:vector-search-sa@your-project-id.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=vector-search-sa@your-project-id.iam.gserviceaccount.com

# run processing script
python scripts/process_documents.py --input-dir ./documents


# run everything locally using Docker:
```
docker-compose up --build
docker-compose run --rm vector-search python scripts/process_documents.py --input-dir /app/documents
```

# build and deploy to Cloud Run
./scripts/deploy.sh
