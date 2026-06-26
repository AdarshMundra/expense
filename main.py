import sys
import os

# Ensure the project root is on sys.path so `app` package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.server import mcp  # noqa: E402

__all__ = ["mcp"]
