# src/processor/gemini_processor.py

import google.generativeai as genai
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import json

from ..config import (
    GEMINI_MODEL,
    GOOGLE_DRIVE_FOLDER_ID,
    SERVICE_ACCOUNT_PATH,
    GEMINI_API_KEY
)
from ..storage.drive import GoogleDriveHandler

logger = logging.getLogger(__name__)

class GeminiProcessor:
    def __init__(self):
        """Initialize Gemini processor with configuration"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
            
        # Configure with API key
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.drive = GoogleDriveHandler(
            credentials_path=SERVICE_ACCOUNT_PATH,
            folder_id=GOOGLE_DRIVE_FOLDER_ID
        )
        
    def _get_mime_type(self, file_path: Path) -> str:
        """Determine mime type based on file extension"""
        ext = file_path.suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.xml': 'text/xml',
            '.rtf': 'text/rtf'
        }
        mime_type = mime_types.get(ext)
        if not mime_type:
            raise ValueError(f"Unsupported file type: {ext}")
        return mime_type
        
    async def process_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a document using Gemini API"""
        try:
            # Read file content
            file_path = Path(file_path)
            mime_type = self._get_mime_type(file_path)
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload to Gemini for analysis
            file = genai.upload_file(str(file_path))
            
            # Process with Gemini
            response = self.model.generate_content([
                file,
                """Please analyze this document and provide:
                1. A structured analysis of the key points and themes
                2. The main topics covered
                3. Important details or specifications
                Format as JSON with keys: 'analysis', 'topics', 'details'"""
            ])
            
            # Parse response
            try:
                analysis_result = json.loads(response.text)
            except json.JSONDecodeError:
                analysis_result = {
                    "analysis": response.text,
                    "topics": [],
                    "details": ""
                }
            
            # Prepare metadata including analysis
            file_metadata = {
                **(metadata or {}),
                'mime_type': mime_type,
                'file_name': file_path.name,
                'analysis': json.dumps(analysis_result.get('analysis', '')),
                'topics': json.dumps(analysis_result.get('topics', [])),
                'details': json.dumps(analysis_result.get('details', ''))
            }
            
            # Upload to Drive with metadata
            drive_result = await self.drive.upload_file(
                file_content,
                file_path.name,
                mime_type,
                metadata=file_metadata
            )
            
            # Return combined results
            return {
                'drive_link': drive_result['web_link'],
                'file_id': drive_result['file_id'],
                'analysis': analysis_result.get('analysis', ''),
                'topics': analysis_result.get('topics', []),
                'details': analysis_result.get('details', ''),
                'metadata': {
                    **file_metadata,
                    'download_link': drive_result['web_link']
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}", exc_info=True)
            raise