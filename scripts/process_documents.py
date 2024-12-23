# scripts/process_documents.py

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.storage import GCSHandler
from src.indexer import DocumentProcessor
from src.config import DOCUMENTS_PREFIX

def main():
    # load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='upload and process documents')
    parser.add_argument('--input-dir', required=True, help='directory containing documents')
    args = parser.parse_args()
    
    # initialize handlers
    gcs = GCSHandler(os.getenv('BUCKET_NAME'))
    processor = DocumentProcessor(
        os.getenv('PROJECT_ID'),
        os.getenv('LOCATION')
    )
    
    # process all files in directory
    input_dir = Path(args.input_dir)
    for file_path in input_dir.glob('*'):
        if file_path.is_file():
            print(f"processing {file_path.name}...")
            
            # upload to GCS
            gcs_path = f"{DOCUMENTS_PREFIX}{file_path.name}"
            gcs.upload_file(str(file_path), gcs_path)
            print(f"uploaded to GCS: {gcs_path}")
            
            # process and index
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                processor.process_and_index_document(
                    content=content,
                    metadata={
                        "filename": file_path.name,
                        "gcs_path": gcs_path
                    }
                )
            print(f"Indexed: {file_path.name}")

if __name__ == "__main__":
    main()
