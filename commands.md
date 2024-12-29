# core setup
export PROJECT_ID=semantcai
export LOCATION=us-central1
export BUCKET_NAME=semantcai-slack-ai-document-search
export SLACK_BOT_TOKEN=xoxb-8082366857367-8212695584051-p2grHtBQCMwhxSFYZM2BPHLV
export SLACK_SIGNING_SECRET=650ed9fcc0f1611c5371cc361fc7b283
export GEMINI_API_KEY=AIzaSyC7e5FrNHBYUoI1_GDioVYQZkxTp06jSWE
export GOOGLE_DRIVE_FOLDER_ID=1Dg49mPT-Y9JdSEKrBUcamoWnD1Azy63u
export GOOGLE_APPLICATION_CREDENTIALS=/service-account-key.json

# enable apis
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    cloudbuild.googleapis.com cloudresourcemanager.googleapis.com iam.googleapis.com

# organization policy setup
gcloud organizations add-iam-policy-binding 923362929465 \
    --member='user:info@semantc.com' \
    --role='roles/orgpolicy.policyAdmin'

gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountKeyCreation \
    --organization=923362929465

# storage setup
gsutil mb -l us-central1 gs://$BUCKET_NAME
gsutil uniformbucketlevelaccess set on gs://$BUCKET_NAME

# service account setup
gcloud iam service-accounts create document-search-sa \
    --display-name="Document Search Service Account"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:document-search-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:document-search-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:document-search-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=document-search-sa@$PROJECT_ID.iam.gserviceaccount.com

# artifact registry setup
gcloud artifacts repositories create document-search \
    --repository-format=docker \
    --location=$LOCATION \
    --description="Document Search Service Repository"

gcloud auth configure-docker ${LOCATION}-docker.pkg.dev

# deploy
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# verify
SERVICE_URL=$(gcloud run services describe document-search --platform managed --region $LOCATION --format 'value(status.url)')
curl "${SERVICE_URL}/health"

## slack app configuration checklist
1. go to [api.slack.com/apps](https://api.slack.com/apps)
2. create or select your app
3. under "oauth & permissions":
   - add bot token scopes:
     - `app_mentions:read`
     - `chat:write`
     - `commands`
   - install app to workspace
   - copy bot user oauth token (for SLACK_BOT_TOKEN)

4. under "basic information":
   - copy signing secret (for SLACK_SIGNING_SECRET)

5. under "slash commands":
   - create new command:
     - command: `/find`
     - request url: `${SERVICE_URL}/slack/commands`
     - description: "search through documents"
     - usage hint: "[search query]"

6. under "event subscriptions":
   - enable events
   - set request url: `${SERVICE_URL}/slack/events`
   - subscribe to bot events:
     - `app_mention`

7. reinstall app if prompted

## troubleshooting

if you encounter issues:

1. check service status:
```bash
gcloud run services describe document-search --region $LOCATION
```

2. view detailed logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=document-search" --limit 50
```

3. verify environment variables:
```bash
gcloud run services describe document-search --region $LOCATION --format 'yaml(spec.template.spec.containers[0].env)'
```