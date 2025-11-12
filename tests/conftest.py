"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
