"""
SmartKitchen API Server
"""
import os as _os, sys as _sys
from pathlib import Path
_sys.path.insert(0, str(Path(__file__).parent.parent))
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from backend.api import recognize, nutrition, history, members, guidelines, recipes
from backend.modules.face_auth.router import router as face_router
from backend.database import init_db
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smartkitchen")
@asynccontextmanager
async def lifespan(app):
    logger.info("smartkitchen starting...")
    init_db()
    logger.info("db initialized")
    yield
app = FastAPI(title="SmartKitchen API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(recognize.router)
app.include_router(nutrition.router)
app.include_router(history.router)
app.include_router(members.router)
app.include_router(guidelines.router)
app.include_router(recipes.router)
app.include_router(face_router)
@app.get("/")
async def root():
    return {"service": "SmartKitchen", "version": "1.0.0", "status": "running",
        "endpoints": {
            "POST /api/recognize": "upload image",
            "GET /api/nutrition": "nutrition query",
            "POST /api/log": "log food",
            "GET /api/history": "history",
            "GET /api/face-auth/status": "face recognition",
        }}
@app.get("/health")
async def health():
    return {"status": "ok"}
@app.exception_handler(Exception)
async def handler(request, exc):
    logger.error(str(exc))
    return JSONResponse(status_code=500, content={"detail": str(exc)})
if __name__ == "__main__":
    port = int(_os.environ.get("PORT", 8686))
    uvicorn.run("backend.app:app", host="127.0.0.1", port=port, reload=True)
