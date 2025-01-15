# src/utils/gemini_cache.py

import google.generativeai as genai
from google.generativeai import caching
import logging
from typing import List, Optional, Dict, Any, Union
import io

logger = logging.getLogger(__name__)

class GeminiCache:
    def __init__(self, model_name: str, system_instruction: str):
        """Initialize the Gemini cache handler
        
        Args:
            model_name: The Gemini model to use (e.g., "gemini-1.5-pro-latest")
            system_instruction: The system instruction for the model
        """
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.cache = None
        self.cached_model = None

    async def create_cache(self, documents: List[Union[bytes, str]], mime_types: List[str]) -> None:
        """Create a cache from the provided documents
        
        Args:
            documents: List of document contents (bytes or str)
            mime_types: List of MIME types corresponding to each document
        """
        try:
            # Upload each document using the File API
            uploaded_docs = []
            for doc, mime_type in zip(documents, mime_types):
                if isinstance(doc, str):
                    doc = doc.encode('utf-8')
                doc_data = io.BytesIO(doc)
                uploaded_doc = genai.upload_file(data=doc_data, mime_type=mime_type)
                uploaded_docs.append(uploaded_doc)

            # Create the cached content
            self.cache = caching.CachedContent.create(
                model=self.model_name,
                system_instruction=self.system_instruction,
                contents=uploaded_docs
            )

            # Initialize the model from cached content
            self.cached_model = genai.GenerativeModel.from_cached_content(self.cache)
            
            logger.info(f"Successfully created cache with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error creating cache: {str(e)}")
            raise

    async def generate_content(self, prompt: str) -> Dict[str, Any]:
        """Generate content using the cached model
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            Dictionary containing the response text and metadata
        """
        if not self.cached_model:
            raise ValueError("Cache not initialized. Call create_cache first.")
            
        try:
            response = self.cached_model.generate_content(prompt)
            
            return {
                'text': response.text,
                'usage_metadata': response.usage_metadata._asdict() if response.usage_metadata else None
            }
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache"""
        if not self.cache:
            return {'status': 'Not initialized'}
            
        return {
            'status': 'Active',
            'model': self.model_name,
            'system_instruction': self.system_instruction,
            'cache_details': str(self.cache)
        }