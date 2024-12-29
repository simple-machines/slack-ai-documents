# src/storage/drive.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, HttpError
from typing import Optional, Dict, List, Any
import io
import json
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    def __init__(self, credentials_path: str, folder_id: Optional[str] = None):
        """Initialize Google Drive client with service account credentials"""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.metadata'
                ]
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = folder_id
            
            # Share folder with service account if folder_id is provided
            if self.folder_id:
                self._ensure_folder_access()
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {str(e)}")
            raise

    def _ensure_folder_access(self) -> None:
        """Ensure service account has access to the folder"""
        try:
            # First check if we already have access
            try:
                self.service.files().get(fileId=self.folder_id, fields='id, name').execute()
                logger.info("Service account already has access to the folder")
                return
            except HttpError as e:
                if e.resp.status != 404:  # If error is not "not found"
                    logger.info("Need to grant folder access to service account")

            # Get service account email from credentials
            service_account_email = self.credentials.service_account_email

            # Create permission for service account
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': service_account_email
            }

            try:
                self.service.permissions().create(
                    fileId=self.folder_id,
                    body=permission,
                    fields='id',
                    sendNotificationEmail=False
                ).execute()
                logger.info(f"Successfully granted folder access to {service_account_email}")
            except HttpError as e:
                logger.error(f"Failed to share folder: {str(e)}")
                if 'insufficientPermissions' in str(e):
                    logger.warning(
                        "Please manually share the folder with the service account email: "
                        f"{service_account_email}"
                    )
                raise

        except Exception as e:
            logger.error(f"Error ensuring folder access: {str(e)}")
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

            # Upload the file with retry logic
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    logger.info(f"Attempting to upload file {filename} (attempt {retry_count + 1}/{max_retries})")
                    
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
                        body=permission,
                        fields='id'
                    ).execute()
                    
                    logger.info(f"Successfully uploaded file {filename} to Drive")
                    
                    return {
                        'file_id': file['id'],
                        'web_link': file['webViewLink'],
                        'properties': file.get('properties', {})
                    }
                    
                except HttpError as e:
                    retry_count += 1
                    last_error = e
                    
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        logger.warning(f"Upload attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed to upload after {max_retries} attempts")
                        raise last_error

        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {str(e)}")
            raise

    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive"""
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    request = self.service.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                        
                    return fh.getvalue()
                
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"Download attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Failed to download file from Drive: {str(e)}")
            raise

    async def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in the specified folder"""
        try:
            # Build the query
            base_query = f"'{self.folder_id}' in parents" if self.folder_id else None
            final_query = f"{base_query} and {query}" if query else base_query
            
            # Get files with retry logic
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    results = []
                    page_token = None
                    
                    while True:
                        response = self.service.files().list(
                            q=final_query,
                            spaces='drive',
                            fields='nextPageToken, files(id, name, mimeType, webViewLink, properties)',
                            pageToken=page_token,
                            orderBy='modifiedTime desc'
                        ).execute()
                        
                        results.extend(response.get('files', []))
                        page_token = response.get('nextPageToken')
                        
                        if not page_token:
                            break
                    
                    return results
                    
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"List files attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Failed to list files in Drive: {str(e)}")
            raise

    async def update_metadata(self, file_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update file metadata"""
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    file_metadata = {'properties': metadata}
                    updated_file = self.service.files().update(
                        fileId=file_id,
                        body=file_metadata,
                        fields='id, properties'
                    ).execute()
                    return updated_file.get('properties', {})
                
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"Update metadata attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
            raise

    async def get_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    file = self.service.files().get(
                        fileId=file_id,
                        fields='properties'
                    ).execute()
                    return file.get('properties', {})
                
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"Get metadata attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.service.files().delete(fileId=file_id).execute()
                    return True
                
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"Delete attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file from Drive: {str(e)}")
            return False