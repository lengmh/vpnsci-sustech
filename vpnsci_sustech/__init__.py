"""vpnsci-sustech - SUSTech-oriented academic paper fetcher and MCP toolset."""

from .config import Config
from .fetcher import PaperFetcher
from .models import Paper
from . import http_clients

__all__ = ["PaperFetcher", "Paper", "Config", "http_clients"]
__version__ = "0.1.0"
