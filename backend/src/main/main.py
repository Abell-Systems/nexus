"""Main entry point for Nexus backend application."""

import sys
from pathlib import Path

# Ensure src/main is on sys.path
SRC_MAIN_DIR = Path(__file__).resolve().parent
if str(SRC_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_MAIN_DIR))

from infrastructure.api import app

__all__ = ["app"]
