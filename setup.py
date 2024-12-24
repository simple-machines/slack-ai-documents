# setup.py

from setuptools import setup, find_packages

setup(
    name="vector-search",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'uvicorn',
        'google-cloud-storage',
        'faiss-cpu',
        'vertexai',
        'python-dotenv',
        'tqdm',
        'numpy',  # required for FAISS and vector operations
        'scikit-learn',  # required for TfidfVectorizer in hybrid_searcher.py
        'python-multipart',  # required for FastAPI file uploads
        'langchain-text-splitters',  # required for document processing
        'pydantic',  # required for FastAPI models
    ],
    python_requires='>=3.9',  # since you're using Python 3.9 in Dockerfile
)