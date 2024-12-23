# scripts/build_index.py

import os
import argparse
from src.indexer import DocumentProcessor
from src.config import PROJECT_ID, LOCATION

def main():
    parser = argparse.ArgumentParser(description='build search index from documents')
    parser.add_argument('--input-dir', required=True, help='directory containing documents')
    args = parser.parse_args()

    processor = DocumentProcessor(PROJECT_ID, LOCATION)
    
    # process all files in directory
    for filename in os.listdir(args.input_dir):
        filepath = os.path.join(args.input_dir, filename)
        if os.path.isfile(filepath):
            print(f"processing {filename}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                processor.process_and_index_document(
                    content=content,
                    metadata={"filename": filename}
                )

    print("index building complete!")

if __name__ == "__main__":
    main()
