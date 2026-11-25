"""
Production entry point: one service for the whole app.

    /api/...   -> the FastAPI backend (backend.api.main)
    /...       -> the built React app (frontend/wisemarket/dist),
                  with index.html for every client-side route

Same origin for both, so no CORS setup and only one URL to share.

    uvicorn backend.api.serve:app --host 0.0.0.0 --port 8000
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.api.main import app as api

DIST = Path(os.environ.get("FRONTEND_DIST", "frontend/wisemarket/dist")).resolve()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Mounted apps don't run their own startup, so run the API's here
    async with api.router.lifespan_context(api):
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    index = DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Frontend not built: run `npm run build` in frontend/wisemarket")
    file = (DIST / path).resolve()
    if path and file.is_file() and DIST in file.parents:
        headers = {"Cache-Control": "public, max-age=31536000, immutable"} if path.startswith("assets/") else None
        return FileResponse(file, headers=headers)
    # client-side routes (/product/123, /basket ...) and unknown paths
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
