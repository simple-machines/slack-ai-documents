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
        'tqdm'
    ],
)