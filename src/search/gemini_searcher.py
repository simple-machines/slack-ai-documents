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
        """initialize Gemini searcher"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # configure with API key
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.gcs = GCSHandler(bucket_name=BUCKET_NAME)

    def _clean_json_response(self, text: str) -> str:
        """clean the response text to get valid JSON"""
        # remove markdown code block markers
        text = text.replace('```json', '').replace('```', '')
        # remove leading/trailing whitespace
        text = text.strip()
        return text

    def _get_mime_type(self, ext: str) -> str:
        """determine mime type based on file extension"""
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
            mime_type = 'text/plain'  # default to text/plain if unknown
        return mime_type

    async def search(self, query: str) -> List[Dict]:
        """search through documents using Gemini"""
        try:
            # get list of documents
            files = await self.gcs.list_files(prefix=DOCUMENTS_PREFIX)
            doc_files = [f for f in files if not f.endswith('_analysis.json')]

            if not doc_files:
                logger.warning("No documents found to search")
                return []

            # create temporary files for processing
            temp_files = []
            for file_path in doc_files:
                try:
                    content = await self.gcs.download_as_bytes(file_path)
                    ext = Path(file_path).suffix.lower()
                    mime_type = self._get_mime_type(ext)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(content)
                        tmp.flush()
                        temp_files.append((tmp.name, Path(file_path).name, mime_type))
                except Exception as e:
                    logger.error(f"error loading file {file_path}: {str(e)}")
                    continue

            try:
                # create temporary file for query
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp:
                    temp_path = temp.name
                    temp.write(query)
                    temp.flush()

                # upload files to Gemini
                query_file = genai.upload_file(temp_path, mime_type='text/plain')
                
                gemini_files = []
                for temp_path, original_name, mime_type in temp_files:
                    file = genai.upload_file(temp_path, mime_type=mime_type)
                    gemini_files.append((file, original_name))

                # enhanced search prompt
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

                # generate search results
                content_parts = [file for file, _ in gemini_files]
                content_parts.append(prompt)

                response = self.model.generate_content(content_parts)

                try:
                    cleaned_response = self._clean_json_response(response.text)
                    results = json.loads(cleaned_response)

                    if not isinstance(results, list):
                        logger.error(f"unexpected response format: {response.text}")
                        return []

                    # log raw results
                    logger.info(f"Raw Gemini results with scores: {[res.get('score') for res in results]}")

                    # filter results by individual score >= 0.90
                    filtered_results = [result for result in results if result.get('score', 0) >= 0.90]
                    logger.info(f"Filtered Gemini results (score >= 0.90): {[res.get('score') for res in filtered_results]}")

                    # format results and apply top_p logic with cumulative threshold
                    formatted_results = []
                    cumulative_score = 0.0
                    
                    # sort by score in descending order
                    for result in sorted(filtered_results, key=lambda x: x.get('score', 0), reverse=True):
                        score = float(result.get('score', 0))
                        if cumulative_score + score <= TOP_P_THRESHOLD:
                            formatted_results.append({
                                'text': result.get('text', ''),
                                'score': score,
                                'metadata': {
                                    'filename': result.get('source', ''),
                                    'page': result.get('page', 1),
                                    'relevance_explanation': result.get('explanation', '')
                                }
                            })
                            cumulative_score += score
                        else:
                            break

                    return formatted_results

                except json.JSONDecodeError as e:
                    logger.error(f"failed to parse Gemini response: {response.text}")
                    logger.error(f"JSON parse error: {str(e)}")
                    return []

            finally:
                # clean up temporary files
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                for temp_path, _, _ in temp_files:
                    try:
                        Path(temp_path).unlink()
                    except Exception as e:
                        logger.error(f"error cleaning up temp file {temp_path}: {str(e)}")

        except Exception as e:
            logger.error(f"search error: {str(e)}", exc_info=True)
            raise
