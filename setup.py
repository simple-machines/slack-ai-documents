# setup.py

from setuptools import setup, find_packages

setup(
    name="gemini-search",  # Updated name to reflect new architecture
    version="0.2.0",      # Bumped version
    packages=find_packages(),
    install_requires=[
        # core google cloud
        'google-cloud-storage',
        'google-cloud-aiplatform',
        'google-generativeai>=0.3.0',
        
        # fastapi and web
        'fastapi',
        'uvicorn',
        'python-multipart',
        'requests',
        
        # pdf processing
        'PyPDF2',
        
        # utilities
        'python-dotenv',
        'tqdm',
        
        # slack integration
        'slack-sdk',
        
        # type checking and api models
        'pydantic',
        
        # async support
        'aiofiles',
    ],
    python_requires='>=3.9',
)
