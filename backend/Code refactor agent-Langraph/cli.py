"""
cli.py — Backward-compatibility shim.

The real implementation lives in app/cli.py.
Run with:
    python cli.py --path /my/project
    python -m app.cli --path /my/project   # preferred

Do not add logic here — edit app/cli.py instead.
"""

from app.cli import main  # noqa: F401

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())