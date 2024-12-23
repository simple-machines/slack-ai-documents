# src/storage/gcs.py

import json
import tempfile
from pathlib import Path
from typing import Optional, Union, BinaryIO
from google.cloud import storage
from google.cloud.storage.blob import Blob
from google.cloud.storage.bucket import Bucket

class GCSHandler:
    def __init__(self, bucket_name: str):
        """initialize GCS client and get bucket reference"""
        self.client = storage.Client()
        self.bucket: Bucket = self.client.bucket(bucket_name)

    def upload_file(self, source_file: Union[str, Path], destination_blob_name: str) -> None:
        """upload a file to GCS bucket"""
        blob: Blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(str(source_file))

    def download_file(self, source_blob_name: str, destination_file: Union[str, Path]) -> None:
        """download a file from GCS bucket"""
        blob: Blob = self.bucket.blob(source_blob_name)
        blob.download_to_filename(str(destination_file))

    def upload_from_string(self, data: str, destination_blob_name: str) -> None:
        """upload string data to GCS bucket"""
        blob: Blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(data)

    def download_as_string(self, source_blob_name: str) -> str:
        """download and return file contents as string"""
        blob: Blob = self.bucket.blob(source_blob_name)
        return blob.download_as_string().decode("utf-8")

    def upload_json(self, data: dict, destination_blob_name: str) -> None:
        """upload dictionary as JSON to GCS bucket"""
        json_str = json.dumps(data)
        self.upload_from_string(json_str, destination_blob_name)

    def download_json(self, source_blob_name: str) -> dict:
        """download and parse JSON file from GCS bucket"""
        content = self.download_as_string(source_blob_name)
        return json.loads(content)

    def list_files(self, prefix: Optional[str] = None) -> list[str]:
        """list all files in bucket with optional prefix"""
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        return [blob.name for blob in blobs]

    def file_exists(self, blob_name: str) -> bool:
        """check if file exists in bucket"""
        blob = self.bucket.blob(blob_name)
        return blob.exists()

    def delete_file(self, blob_name: str) -> None:
        """delete a file from bucket"""
        blob = self.bucket.blob(blob_name)
        blob.delete()
