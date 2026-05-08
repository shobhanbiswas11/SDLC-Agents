#!/usr/bin/env python3
"""
Entry point for running the Dependency Resolver Agent backend.
Usage: python run.py
"""

import sys
import uvicorn
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        ws_max_size=65536,
    )
