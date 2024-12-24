# src/__init__.py

from . import api
from . import config
from . import indexer
from . import search
from . import storage

__version__ = "0.1.0"

# export commonly used classes
from .indexer import DocumentProcessor
from .search import HybridSearcher
from .storage import IndexStore

__all__ = [
    "DocumentProcessor",
    "HybridSearcher", 
    "IndexStore",
    "api",
    "config",
    "indexer",
    "search",
    "storage",
]
