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

        # Configure with API key
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

    async def search(self, query: str) -> List[Dict]:
        """
        search through documents using Gemini, returning results until the relevance threshold is met,
        considering only results with an individual score of 0.85 or higher.

        args:
            query: search query string

        returns:
            list of search results with scores and metadata
        """
        try:
            # get list of documents
            files = await self.gcs.list_files(prefix=DOCUMENTS_PREFIX)

            # filter out analysis files
            doc_files = [f for f in files if not f.endswith('_analysis.json')]

            if not doc_files:
                logger.warning("No documents found to search")
                return []

            # create temporary files for processing
            temp_files = []
            for file_path in doc_files:
                try:
                    # download file content to temp file
                    content = await self.gcs.download_as_bytes(file_path)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_path).suffix) as tmp:
                        tmp.write(content)
                        temp_files.append((tmp.name, Path(file_path).name))

                except Exception as e:
                    logger.error(f"error loading file {file_path}: {str(e)}")
                    continue

            try:
                # upload files to Gemini
                gemini_files = []
                for temp_path, original_name in temp_files:
                    file = genai.upload_file(temp_path)
                    gemini_files.append((file, original_name))

                # Create search prompt
                prompt = f"""
                Search Query: {query}

                Search through the provided documents and return relevant results that answer the query.
                For each result, provide:
                1. The text passage that answers the query.
                2. A relevance score between 0 and 1.
                3. An explanation of how this passage answers the query.
                4. The source document name.

                Format the response as a JSON array of objects with these exact keys:
                - text: the relevant text passage
                - score: a float between 0 and 1
                - explanation: why this is relevant
                - source: the document name
                """

                # generate search results
                content_parts = [file for file, _ in gemini_files]
                content_parts.append(prompt)

                response = self.model.generate_content(content_parts)

                # parse and format results
                try:
                    # clean the response text before parsing
                    cleaned_response = self._clean_json_response(response.text)
                    results = json.loads(cleaned_response)

                    if not isinstance(results, list):
                        logger.error(f"unexpected response format: {response.text}")
                        return []

                    # Log the scores of the raw results for debugging
                    logger.info(f"Raw Gemini results with scores: {[res.get('score') for res in results]}")

                    # Filter results by individual score >= 0.85
                    filtered_results = [result for result in results if result.get('score', 0) >= 0.85]
                    logger.info(f"Filtered Gemini results (score >= 0.85): {[res.get('score') for res in filtered_results]}")

                    # format results and apply top_p logic
                    formatted_results = []
                    cumulative_score = 0.0
                    for result in sorted(filtered_results, key=lambda x: x.get('score', 0), reverse=True):
                        score = float(result.get('score', 0))
                        if cumulative_score + score <= TOP_P_THRESHOLD:
                            formatted_results.append({
                                'text': result.get('text', ''),
                                'score': score,
                                'metadata': {
                                    'filename': result.get('source', ''),
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
                for temp_path, _ in temp_files:
                    try:
                        Path(temp_path).unlink()
                    except Exception as e:
                        logger.error(f"error cleaning up temp file {temp_path}: {str(e)}")

        except Exception as e:
            logger.error(f"search error: {str(e)}", exc_info=True)
            raise
