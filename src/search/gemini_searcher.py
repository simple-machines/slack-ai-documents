import google.generativeai as genai
from typing import List, Dict, Any
import logging
import json
from pathlib import Path
import tempfile

from ..config import (
    PROJECT_ID,
    LOCATION,
    GEMINI_MODEL,
    TOP_K,
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
    
    def _clean_json_response(self, text: str) -> str:
        """Clean the response text to get valid JSON"""
        # Remove markdown code block markers
        text = text.replace('```json', '').replace('```', '')
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
        
    async def search(self, query: str, k: int = TOP_K) -> List[Dict]:
        """
        Search through documents using Gemini
        
        Args:
            query: Search query string
            k: Number of results to return
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Get list of documents
            files = await self.gcs.list_files(prefix=DOCUMENTS_PREFIX)
            
            # Filter out analysis files
            doc_files = [f for f in files if not f.endswith('_analysis.json')]
            
            if not doc_files:
                logger.warning("No documents found to search")
                return []
            
            # Create temporary files for processing
            temp_files = []
            for file_path in doc_files:
                try:
                    # Download file content to temp file
                    content = await self.gcs.download_as_bytes(file_path)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_path).suffix) as tmp:
                        tmp.write(content)
                        temp_files.append((tmp.name, Path(file_path).name))
                        
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {str(e)}")
                    continue
            
            try:
                # Upload files to Gemini
                gemini_files = []
                for temp_path, original_name in temp_files:
                    file = genai.upload_file(temp_path)
                    gemini_files.append((file, original_name))
                
                # Create search prompt
                prompt = f"""
                Search Query: {query}
                
                Search through the provided documents and return the {k} most relevant results.
                For each result, provide:
                1. The relevant text passage
                2. A relevance score between 0 and 1
                3. A brief explanation of why this passage is relevant
                4. The source document name
                
                Format the response as a JSON array of objects with these exact keys:
                - text: the relevant text passage
                - score: a float between 0 and 1
                - explanation: why this is relevant
                - source: the document name
                """
                
                # Generate search results
                content_parts = [file for file, _ in gemini_files]
                content_parts.append(prompt)
                
                # Remove await here
                response = self.model.generate_content(content_parts)
                
                # Parse and format results
                try:
                    # Clean the response text before parsing
                    cleaned_response = self._clean_json_response(response.text)
                    results = json.loads(cleaned_response)
                    
                    if not isinstance(results, list):
                        logger.error(f"Unexpected response format: {response.text}")
                        return []
                    
                    # Format results
                    formatted_results = []
                    for result in results[:k]:
                        formatted_results.append({
                            'text': result.get('text', ''),
                            'score': float(result.get('score', 0)),
                            'metadata': {
                                'filename': result.get('source', ''),
                                'relevance_explanation': result.get('explanation', '')
                            }
                        })
                    
                    return formatted_results
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini response: {response.text}")
                    logger.error(f"JSON parse error: {str(e)}")
                    return []
                    
            finally:
                # Clean up temporary files
                for temp_path, _ in temp_files:
                    try:
                        Path(temp_path).unlink()
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file {temp_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            raise
