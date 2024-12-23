# AI Vector Search Service

A cost-effective hybrid search service that combines semantic search using FAISS with Google Cloud's AI services. This service provides similar functionality to Vertex AI Vector Search at a fraction of the cost.

## Architecture

The service consists of:
- FAISS for efficient vector similarity search
- Google Cloud Storage for document and index storage
- Vertex AI Text Embeddings for semantic understanding
- FastAPI for serving search requests
- Docker for containerization
- Cloud Run for deployment

## Cost Benefits

This implementation is significantly more cost-effective than Vertex AI Vector Search:
- Embeddings API: ~$0.10 per 1000 text chunks
- GCS Storage: ~$0.02/GB/month
- Cloud Run: Pay per use
- FAISS: Free, open source

Example cost estimate for 1000 documents:
- Initial indexing: ~$1-2
- 1000 searches: ~$0.70
- Storage and Cloud Run: <$1/month

## Prerequisites

- Google Cloud Project
- Service Account with permissions for:
  - Cloud Storage
  - Vertex AI
  - Cloud Run (if deploying)
- Docker and Docker Compose installed

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd slack-ai-vector-search
```

2. Create service account and download key:
```bash
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

3. Create .env file:
```bash
PROJECT_ID=your-project-id
LOCATION=us-central1
BUCKET_NAME=your-bucket-name
```

4. Create GCS bucket:
```bash
gsutil mb -l us-central1 gs://[BUCKET_NAME]
```

## Development

1. Start the service:
```bash
docker-compose up --build
```

2. Process documents:
```bash
# Place documents in ./documents directory
docker-compose run --rm vector-search python scripts/process_documents.py --input-dir /app/documents
```

3. Test the API:
- Open http://localhost:8080/docs in your browser
- Use the interactive Swagger UI to test search endpoints

## API Endpoints

### POST /search
Search for documents similar to a query.

Request body:
```json
{
  "query": "your search query",
  "top_k": 5
}
```

Response:
```json
[
  {
    "text": "matched text",
    "score": 0.85,
    "metadata": {
      "filename": "document.pdf",
      "gcs_path": "documents/document.pdf"
    }
  }
]
```

## Deployment

Deploy to Cloud Run:
```bash
./scripts/deploy.sh
```

## Supported File Types

Current implementation supports:
- PDF files (.pdf)
- Text files (.txt)

## Project Structure

```
slack-ai-vector-search/
├── Dockerfile
├── docker-compose.yml
├── setup.py
├── requirements.txt
├── src/
│   ├── api/          # FastAPI application
│   ├── config/       # Configuration
│   ├── indexer/      # Document processing
│   ├── search/       # Search implementation
│   └── storage/      # GCS operations
└── scripts/
    ├── build_index.py
    └── process_documents.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.