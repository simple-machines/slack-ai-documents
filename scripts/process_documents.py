# scripts/process_documents.py

import os
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import asyncio
from src.storage import GCSHandler
from src.processor.gemini_processor import GeminiProcessor
from src.config import DOCUMENTS_PREFIX

async def process_file(file_path: Path, processor: GeminiProcessor, gcs: GCSHandler) -> None:
    """Process a single file using Gemini"""
    try:
        print(f"Processing {file_path.name}...")
        
        # Upload to GCS
        gcs_path = f"{DOCUMENTS_PREFIX}{file_path.name}"
        await gcs.upload_file(str(file_path), gcs_path)
        print(f"Uploaded to GCS: {gcs_path}")
        
        # Process with Gemini
        result = await processor.process_document(
            str(file_path),
            metadata={
                "filename": file_path.name,
                "gcs_path": gcs_path
            }
        )
        print(f"Processed document: {file_path.name}")
        print(f"Analysis summary: {result['analysis'][:200]}...")
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

async def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Process documents with Gemini')
    parser.add_argument('--input-dir', required=True, help='directory containing documents')
    args = parser.parse_args()
    
    # Initialize handlers
    gcs = GCSHandler(os.getenv('BUCKET_NAME'))
    processor = GeminiProcessor()
    
    # Process all files in directory
    input_dir = Path(args.input_dir)
    tasks = []
    
    for file_path in input_dir.glob('*'):
        if file_path.is_file():
            tasks.append(process_file(file_path, processor, gcs))
    
    # Process files concurrently
    await asyncio.gather(*tasks)
    print("Document processing complete!")

if __name__ == "__main__":
    asyncio.run(main())
