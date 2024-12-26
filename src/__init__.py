# src/__init__.py

from . import api
from . import config
from . import processor
from . import search
from . import storage
from . import utils

__version__ = "0.2.0"

# export commonly used classes
from .processor import GeminiProcessor
from .search import GeminiSearcher
from .storage import GCSHandler

__all__ = [
    "GeminiProcessor",
    "GeminiSearcher", 
    "GCSHandler",
    "api",
    "config",
    "processor",
    "search",
    "storage",
    "utils"
]
