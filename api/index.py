"""
Vercel ASGI entry point for GraphOne.

Vercel's Python runtime expects an ASGI-compatible `app` object in api/*.py files.
We bridge the existing aiohttp.web application to ASGI using aiohttp-asgi.
"""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports resolve correctly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aiohttp_asgi import AiohttpAsgiAdapter
from src.server import create_app

# Build the aiohttp application
_aiohttp_app = create_app()

# Wrap it in an ASGI adapter — this is what Vercel's Python runtime calls
app = AiohttpAsgiAdapter(_aiohttp_app)
