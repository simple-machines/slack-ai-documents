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
    DOCUMENTS_PREFIX,
    BUCKET_NAME,
    GEMINI_API_KEY
)
from ..storage.gcs import GCSHandler

logger = logging.getLogger(__name__)

class GeminiSearcher:
    def __init__(self):
        """Initialize Gemini searcher"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure with API key
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.gcs = GCSHandler(bucket_name=BUCKET_NAME)
        
    async def _get_actual_filename(self, doc_files: List[str], source: str) -> str:
        """Match the source name to actual file in GCS bucket"""
        # If the source matches exactly, return it
        if source in doc_files:
            return source
            
        # Clean up source name and try to match
        source_clean = source.lower().replace(" ", "_")
        for file in doc_files:
            if file.lower().endswith('.pdf'):
                return file
                
        # If no match found, return original source
        return source

    async def _get_document_metadata(self, filename: str, doc_files: List[str]) -> Dict[str, Any]:
        """Get document metadata including download link from analysis file"""
        try:
            # Get actual filename from GCS
            actual_filename = await self._get_actual_filename(doc_files, filename)
            logger.info(f"Matched source '{filename}' to actual file '{actual_filename}'")
            
            # Try to get the analysis file if it exists
            try:
                analysis_path = f"{DOCUMENTS_PREFIX}analysis/{Path(actual_filename).stem}_analysis.json"
                metadata = await self.gcs.download_json(analysis_path)
                return {
                    'filename': filename,  # Keep original name for display
                    'actual_filename': actual_filename,  # Store actual filename
                    'download_link': metadata.get('drive_link', ''),
                    'mime_type': metadata.get('metadata', {}).get('mime_type', '')
                }
            except Exception as analysis_error:
                logger.info(f"Analysis file not found for {actual_filename}, using basic metadata")
                return {
                    'filename': filename,
                    'actual_filename': actual_filename,
                    'download_link': '',
                    'mime_type': self._get_mime_type(Path(actual_filename).suffix)
                }
                
        except Exception as e:
            logger.error(f"Error getting metadata for {filename}: {str(e)}")
            return {'filename': filename}

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

    async def search(self, query: str) -> List[Dict]:
        """Search through documents using Gemini"""
        try:
            # Get list of documents
            files = await self.gcs.list_files(prefix=DOCUMENTS_PREFIX)
            doc_files = [Path(f).name for f in files if not f.endswith('_analysis.json')]

            if not doc_files:
                logger.warning("No documents found to search")
                return []

            # Create temporary files for processing
            temp_files = []
            for file_path in files:
                try:
                    if file_path.endswith('_analysis.json'):
                        continue
                    content = await self.gcs.download_as_bytes(file_path)
                    ext = Path(file_path).suffix.lower()
                    mime_type = self._get_mime_type(ext)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(content)
                        tmp.flush()
                        temp_files.append((tmp.name, Path(file_path).name, mime_type))
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {str(e)}")
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

                    if not isinstance(results, list):
                        logger.error(f"Unexpected response format: {response.text}")
                        return []

                    # Filter results by individual score >= 0.90
                    filtered_results = [result for result in results if result.get('score', 0) >= 0.90]
                    
                    # Format results and apply top_p logic with cumulative threshold
                    formatted_results = []
                    cumulative_score = 0.0
                    
                    # Sort by score in descending order
                    for result in sorted(filtered_results, key=lambda x: x.get('score', 0), reverse=True):
                        score = float(result.get('score', 0))
                        if cumulative_score + score <= TOP_P_THRESHOLD:
                            # Get metadata including download link
                            metadata = await self._get_document_metadata(result.get('source', ''), doc_files)
                            
                            formatted_results.append({
                                'text': result.get('text', ''),
                                'score': score,
                                'metadata': {
                                    **metadata,
                                    'relevance_explanation': result.get('explanation', '')
                                }
                            })
                            cumulative_score += score
                        else:
                            break

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
