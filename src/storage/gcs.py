# src/storage/gcs.py

import json
import tempfile
from pathlib import Path
from typing import Optional, Union, BinaryIO, List
import logging
from google.cloud import storage
from google.cloud.storage.blob import Blob
from google.cloud.storage.bucket import Bucket
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class GCSHandler:
    def __init__(self, bucket_name: str):
        """initialize GCS client and get bucket reference"""
        self.client = storage.Client()
        self.bucket: Bucket = self.client.bucket(bucket_name)
        self._executor = ThreadPoolExecutor(max_workers=5)

    async def upload_file(self, source_file: Union[str, Path], destination_blob_name: str) -> None:
        """upload a file to GCS bucket"""
        try:
            blob: Blob = self.bucket.blob(destination_blob_name)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self._executor,
                blob.upload_from_filename,
                str(source_file)
            )
        except Exception as e:
            logger.error(f"error uploading file to GCS: {str(e)}")
            raise

    async def download_file(self, source_blob_name: str, destination_file: Union[str, Path]) -> None:
        """download a file from GCS bucket"""
        try:
            blob: Blob = self.bucket.blob(source_blob_name)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self._executor,
                blob.download_to_filename,
                str(destination_file)
            )
        except Exception as e:
            logger.error(f"error downloading file from GCS: {str(e)}")
            raise

    async def upload_from_string(self, data: str, destination_blob_name: str) -> None:
        """upload string data to GCS bucket"""
        try:
            blob: Blob = self.bucket.blob(destination_blob_name)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self._executor,
                blob.upload_from_string,
                data
            )
        except Exception as e:
            logger.error(f"error uploading string to GCS: {str(e)}")
            raise

    async def download_as_string(self, source_blob_name: str) -> str:
        """download and return file contents as string"""
        try:
            blob: Blob = self.bucket.blob(source_blob_name)
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                self._executor,
                blob.download_as_string
            )
            return content.decode("utf-8")
        except Exception as e:
            logger.error(f"error downloading string from GCS: {str(e)}")
            raise

    async def upload_json(self, data: dict, destination_blob_name: str) -> None:
        """upload dictionary as JSON to GCS bucket"""
        try:
            json_str = json.dumps(data, indent=2)
            await self.upload_from_string(json_str, destination_blob_name)
        except Exception as e:
            logger.error(f"error uploading JSON to GCS: {str(e)}")
            raise

    async def download_json(self, source_blob_name: str) -> dict:
        """download and parse JSON file from GCS bucket"""
        try:
            content = await self.download_as_string(source_blob_name)
            return json.loads(content)
        except Exception as e:
            logger.error(f"error downloading JSON from GCS: {str(e)}")
            raise

    async def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """list all files in bucket with optional prefix"""
        try:
            loop = asyncio.get_running_loop()
            blobs = await loop.run_in_executor(
                self._executor,
                lambda: list(self.client.list_blobs(self.bucket, prefix=prefix))
            )
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"error listing files in GCS: {str(e)}")
            raise

    async def file_exists(self, blob_name: str) -> bool:
        """check if file exists in bucket"""
        try:
            blob = self.bucket.blob(blob_name)
            loop = asyncio.get_running_loop()
            exists = await loop.run_in_executor(
                self._executor,
                blob.exists
            )
            return exists
        except Exception as e:
            logger.error(f"error checking file existence in GCS: {str(e)}")
            raise

    def __del__(self):
        """cleanup executor on deletion"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    async def download_as_bytes(self, source_blob_name: str) -> bytes:
        """download and return file contents as bytes"""
        try:
            blob: Blob = self.bucket.blob(source_blob_name)
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                self._executor,
                blob.download_as_bytes
            )
            return content
        except Exception as e:
            logger.error(f"error downloading bytes from GCS: {str(e)}")
            raise
