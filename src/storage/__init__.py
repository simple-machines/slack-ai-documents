# src/storage/__init__.py

from .gcs import GCSHandler
from .index_store import IndexStore

__all__ = ['GCSHandler', 'IndexStore']
