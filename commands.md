# create and configure gcs bucket
```
gsutil mb -l us-central1 gs://slack-ai-document-search
```

# set environment variables
```
export PROJECT_ID=semantc-ai
export LOCATION=us-central1
export BUCKET_NAME=slack-ai-document-search
export SLACK_BOT_TOKEN=xoxb-8082366857367-8212695584051-p2grHtBQCMwhxSFYZM2BPHLV
export SLACK_SIGNING_SECRET=650ed9fcc0f1611c5371cc361fc7b283
export GEMINI_API_KEY=AIzaSyC7e5FrNHBYUoI1_GDioVYQZkxTp06jSWE
```

# create service account and download key
```
gcloud iam service-accounts create document-search-sa

gcloud projects add-iam-policy-binding semantc-ai \
    --member="serviceAccount:document-search-sa@semantc-ai.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding semantc-ai \
    --member="serviceAccount:document-search-sa@semantc-ai.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=document-search-sa@semantc-ai.iam.gserviceaccount.com
```

# build and deploy to Cloud Run
```
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```
