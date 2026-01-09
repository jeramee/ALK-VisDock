from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn


def serve(site_dir: str = "site", host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve a previously built site directory."""
    site = Path(site_dir).resolve()
    if not site.exists():
        raise FileNotFoundError(f"Site directory not found: {site}")

    app = FastAPI(title="ALK-VisDock")
    app.mount("/", StaticFiles(directory=str(site), html=True), name="site")

    uvicorn.run(app, host=host, port=port)
