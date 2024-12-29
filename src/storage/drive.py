# src/storage/drive.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from typing import Optional, Dict
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    def __init__(self, credentials_path: str, folder_id: Optional[str] = None):
        """Initialize Google Drive client with service account credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            self.folder_id = folder_id
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {str(e)}")
            raise

    async def upload_file(self, file_content: bytes, filename: str, mime_type: str) -> Dict[str, str]:
        """
        Upload a file to Google Drive and return file details
        
        Args:
            file_content: File content as bytes
            filename: Name of the file
            mime_type: MIME type of the file
            
        Returns:
            Dict containing file ID and shareable link
        """
        try:
            # Prepare the file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id] if self.folder_id else []
            }

            # Create media upload object
            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(fh, mime_type, resumable=True)

            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()

            # Set file sharing permissions (anyone with link can view)
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file['id'],
                body=permission
            ).execute()

            return {
                'file_id': file['id'],
                'web_link': file['webViewLink']
            }

        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {str(e)}")
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Google Drive: {str(e)}")
            return False