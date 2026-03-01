"""
FrigoScan — Point d'entrée principal FastAPI.
Application de gestion de frigo, locale, tactile, sur port 8000.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from server.database import init_db
from server.routers import scan, fridge, recipes, shopping, stats, settings, export_import, seasonal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
).split(",")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("frigoscan")

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FrigoScan",
    description="Application de gestion de frigo — tactile, locale, intelligent.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(scan.router)
app.include_router(fridge.router)
app.include_router(recipes.router)
app.include_router(shopping.router)
app.include_router(stats.router)
app.include_router(settings.router)
app.include_router(export_import.router)
app.include_router(seasonal.router)

# ---------------------------------------------------------------------------
# Fichiers statiques
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Page d'accueil
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    index_path = Path(__file__).parent.parent / "index.html"
    return FileResponse(str(index_path))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "FrigoScan", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Gestionnaire d'erreurs global
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    
    # En production, ne pas exposer la stacktrace
    if DEBUG:
        error_msg = str(exc)
    else:
        error_msg = "Erreur serveur"
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_msg,
            "message": "Une erreur inattendue s'est produite. Veuillez réessayer.",
            "conseil": "Si le problème persiste, vous pouvez restaurer la base depuis les réglages.",
        }
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    logger.info("🧊 FrigoScan v2.0 — Démarrage...")
    init_db()
    logger.info("✅ Base de données initialisée.")
    logger.info("🌐 Application disponible sur http://localhost:8000")


# ---------------------------------------------------------------------------
# Lancement direct
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
