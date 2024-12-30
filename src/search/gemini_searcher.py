# src/search/gemini_searcher.py

import google.generativeai as genai
from typing import List, Dict, Any
import logging
import json
from pathlib import Path
import tempfile

from ..config import (
    GEMINI_MODEL,
    TOP_P_THRESHOLD,
    GOOGLE_DRIVE_FOLDER_ID,
    SERVICE_ACCOUNT_PATH,
    GEMINI_API_KEY
)
from ..storage.drive import GoogleDriveHandler

logger = logging.getLogger(__name__)

class GeminiSearcher:
    def __init__(self):
        """Initialize Gemini searcher"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure with API key
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.drive = GoogleDriveHandler(
            credentials_path=SERVICE_ACCOUNT_PATH,
            folder_id=GOOGLE_DRIVE_FOLDER_ID
        )

    def _clean_json_response(self, text: str) -> str:
        """Clean the response text to get valid JSON"""
        text = text.replace('```json', '').replace('```', '')
        return text.strip()

    def _get_mime_type(self, ext: str) -> str:
        """Determine mime type based on file extension"""
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
        mime_type = mime_types.get(ext.lower())
        if not mime_type:
            mime_type = 'text/plain'
        return mime_type

    async def _get_document_metadata(self, filename: str, drive_files: List[Dict]) -> Dict[str, Any]:
        """Get document metadata from Drive files list"""
        try:
            logger.info(f"Searching for metadata for file: {filename}")
            
            # Store the source name from Gemini for display
            display_name = filename
            
            # Check if any file in drive_files matches our search results
            # Get the first and only file since we know it's the one we're searching
            if drive_files and len(drive_files) > 0:
                file = drive_files[0]  # We only have one file in the Drive folder
                logger.info(f"Using file: {file.get('name')}")
                
                properties = file.get('properties', {})
                # Parse stored JSON properties
                try:
                    analysis = json.loads(properties.get('analysis', '""'))
                    topics = json.loads(properties.get('topics', '[]'))
                    details = json.loads(properties.get('details', '""'))
                except json.JSONDecodeError:
                    analysis, topics, details = "", [], ""
                
                metadata = {
                    'filename': display_name,  # Keep original name for display
                    'download_link': file.get('webViewLink', ''),  # Use the actual file's link
                    'mime_type': file.get('mimeType', ''),
                    'analysis': analysis,
                    'topics': topics,
                    'details': details
                }
                logger.info(f"Returning metadata: {json.dumps(metadata, indent=2)}")
                return metadata
                    
            logger.warning(f"No files found in Drive")
            return {'filename': display_name}
                
        except Exception as e:
            logger.error(f"Error getting metadata for {filename}: {str(e)}")
            return {'filename': filename}

    async def search(self, query: str) -> List[Dict]:
        """Search through documents using Gemini"""
        try:
            # Get list of documents from Drive
            drive_files = await self.drive.list_files()
            if not drive_files:
                logger.warning("No documents found to search")
                return []

            # Log found files
            logger.info(f"Found {len(drive_files)} files in Drive")
            logger.info(f"Files: {[f.get('name') for f in drive_files]}")

            # Create temporary files for processing
            temp_files = []
            for file in drive_files:
                try:
                    content = await self.drive.download_file(file['id'])
                    ext = Path(file['name']).suffix.lower()
                    mime_type = self._get_mime_type(ext)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(content)
                        tmp.flush()
                        temp_files.append((tmp.name, file['name'], mime_type))
                        logger.info(f"Successfully created temp file for {file['name']}")
                except Exception as e:
                    logger.error(f"Error loading file {file['name']}: {str(e)}")
                    continue

            try:
                # Create temporary file for query
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp:
                    temp_path = temp.name
                    temp.write(query)
                    temp.flush()

                # Upload files to Gemini
                query_file = genai.upload_file(temp_path, mime_type='text/plain')
                
                gemini_files = []
                for temp_path, original_name, mime_type in temp_files:
                    file = genai.upload_file(temp_path, mime_type=mime_type)
                    gemini_files.append((file, original_name))

                # Enhanced search prompt
                prompt = f"""
                Search Query: {query}

                Search through the provided documents and find ALL relevant passages that answer or relate to the query.
                Be thorough - if multiple different sections contain relevant information, include them all.
                
                For each relevant passage found, provide:
                1. The complete text passage that contains the answer (preserve full context)
                2. A relevance score between 0 and 1 (be precise in scoring - if multiple passages are equally relevant, give them the same score)
                3. A detailed explanation of how this passage relates to or answers the query
                4. The source document name

                Return ALL passages that are highly relevant (don't limit to just the best match).
                Format each result as a JSON object with these exact keys:
                - text: the complete relevant passage
                - score: a float between 0 and 1
                - explanation: detailed explanation of relevance
                - source: the document name

                Return as a JSON array containing ALL relevant results.
                """

                # Generate search results
                content_parts = [file for file, _ in gemini_files]
                content_parts.append(prompt)
                response = self.model.generate_content(content_parts)

                try:
                    cleaned_response = self._clean_json_response(response.text)
                    results = json.loads(cleaned_response)
                    logger.info(f"Raw Gemini response: {json.dumps(results, indent=2)}")

                    if not isinstance(results, list):
                        logger.error(f"Unexpected response format: {response.text}")
                        return []

                    # Filter results by individual score >= 0.90
                    filtered_results = [result for result in results if result.get('score', 0) >= 0.90]
                    logger.info(f"Filtered results: {json.dumps(filtered_results, indent=2)}")
                    
                    # Format results and apply top_p logic with cumulative threshold
                    formatted_results = []
                    cumulative_score = 0.0
                    
                    # Sort by score in descending order
                    for result in sorted(filtered_results, key=lambda x: x.get('score', 0), reverse=True):
                        score = float(result.get('score', 0))
                        if cumulative_score + score <= TOP_P_THRESHOLD:
                            source_name = result.get('source', '')
                            logger.info(f"Getting metadata for source: {source_name}")
                            
                            # Get metadata including download link
                            metadata = await self._get_document_metadata(source_name, drive_files)
                            logger.info(f"Retrieved metadata: {json.dumps(metadata, indent=2)}")
                            
                            formatted_result = {
                                'text': result.get('text', ''),
                                'score': score,
                                'metadata': {
                                    **metadata,
                                    'relevance_explanation': result.get('explanation', '')
                                }
                            }
                            logger.info(f"Formatted result: {json.dumps(formatted_result, indent=2)}")
                            
                            formatted_results.append(formatted_result)
                            cumulative_score += score
                        else:
                            break

                    logger.info(f"Final formatted results: {json.dumps(formatted_results, indent=2)}")
                    return formatted_results

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini response: {response.text}")
                    logger.error(f"JSON parse error: {str(e)}")
                    return []

            finally:
                # Clean up temporary files
                try:
                    if Path(temp_path).exists():
                        Path(temp_path).unlink()
                except Exception as e:
                    logger.error(f"Error cleaning up query temp file: {str(e)}")
                
                for temp_path, _, _ in temp_files:
                    try:
                        if Path(temp_path).exists():
                            Path(temp_path).unlink()
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file {temp_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            raise