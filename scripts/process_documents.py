# scripts/process_documents.py

import os
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import io
from PyPDF2 import PdfReader
from src.storage import GCSHandler
from src.indexer import DocumentProcessor
from src.config import DOCUMENTS_PREFIX

def extract_text_from_pdf(file_path: Path) -> str:
    """extract text content from PDF file"""
    with open(file_path, 'rb') as file:
        pdf = PdfReader(file)
        text = ''
        for page in pdf.pages:
            text += page.extract_text() + '\n'
        return text

def process_file(file_path: Path) -> Optional[str]:
    """process different file types and return text content"""
    suffix = file_path.suffix.lower()
    
    try:
        if suffix == '.pdf':
            return extract_text_from_pdf(file_path)
        elif suffix == '.txt':
            # For text files, try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"could not decode {file_path} with any known encoding")
        else:
            print(f"unsupported file type: {suffix}")
            return None
    except Exception as e:
        print(f"error processing {file_path}: {str(e)}")
        return None

def main():
    # Load environment variables
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
            
            # extract text content based on file type
            content = process_file(file_path)
            if content:
                # process and index
                processor.process_and_index_document(
                    content=content,
                    metadata={
                        "filename": file_path.name,
                        "gcs_path": gcs_path
                    }
                )
                print(f"indexed: {file_path.name}")
            else:
                print(f"skipped indexing: {file_path.name}")

if __name__ == "__main__":
    main()
