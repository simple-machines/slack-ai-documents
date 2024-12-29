# src/storage/drive.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from typing import Optional, Dict, List, Any
import io
import json
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

    async def upload_file(self, file_content: bytes, filename: str, mime_type: str, metadata: Optional[Dict] = None) -> Dict[str, str]:
        """
        Upload a file to Google Drive and return file details
        
        Args:
            file_content: File content as bytes
            filename: Name of the file
            mime_type: MIME type of the file
            metadata: Optional metadata to store with the file
            
        Returns:
            Dict containing file ID and shareable link
        """
        try:
            # Prepare the file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id] if self.folder_id else [],
                'properties': metadata or {}
            }

            # Create media upload object
            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(fh, mime_type, resumable=True)

            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, properties',
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
                'web_link': file['webViewLink'],
                'properties': file.get('properties', {})
            }

        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {str(e)}")
            raise

    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            return fh.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to download file from Drive: {str(e)}")
            raise

    async def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in the specified folder"""
        try:
            # Build the query
            base_query = f"'{self.folder_id}' in parents" if self.folder_id else None
            final_query = f"{base_query} and {query}" if query else base_query
            
            # Get files
            results = []
            page_token = None
            while True:
                response = self.service.files().list(
                    q=final_query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, webViewLink, properties)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to list files in Drive: {str(e)}")
            raise

    async def update_metadata(self, file_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update file metadata"""
        try:
            file_metadata = {'properties': metadata}
            updated_file = self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, properties'
            ).execute()
            return updated_file.get('properties', {})
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
            raise

    async def get_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='properties'
            ).execute()
            return file.get('properties', {})
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Drive: {str(e)}")
            return False