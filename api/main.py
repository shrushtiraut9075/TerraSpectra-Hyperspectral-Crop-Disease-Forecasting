import os
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routers import analytics, fields, jobs, results, scenes, timeline
from api.services.db import init_db
from api.settings import settings

loaded_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and recovery
    init_db()

    # Seed default farm if DB is empty
    try:
        from api.services.db import list_fields
        if len(list_fields()) == 0:
            from api.services.farm_creator import create_custom_farm
            from api.schemas import FieldCreateRequest
            create_custom_farm(FieldCreateRequest(
                name="Farm Alpha (1,000 Acres, Pune UTM-43N)",
                crop_type="Sugarcane",
                acres=1000.0,
                lat=18.5204,
                lon=73.8567
            ))
            print("[Lifespan] Auto-seeded Farm Alpha default field.")
    except Exception as e:
        print(f"[Lifespan] Note: default farm seeding skipped: {e}")

    # Preload model checkpoint if available
    global loaded_model
    ckpt_path = os.path.join(settings.artifacts_root, "checkpoints", "best_model.pt")
    if os.path.exists(ckpt_path):
        try:
            loaded_model = torch.load(ckpt_path, map_location="cpu")
            print(f"[Lifespan] Loaded model checkpoint: {ckpt_path}")
        except Exception as e:
            print(f"[Lifespan] Warning: could not load model checkpoint: {e}")

    yield

    # Shutdown
    print("[Lifespan] Shutting down TerraSpectra API.")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler for standard error schema per api-spec.md
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": None}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors(),
            }
        },
    )


# Health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "gpu": torch.cuda.is_available(),
        "model_loaded": (loaded_model is not None),
        "version": settings.version,
    }


# Register API v1 routers directly under /api/v1
app.include_router(fields.router, prefix="/api/v1")
app.include_router(scenes.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")


# Alias /api/v1/health -> /health
@app.get("/api/v1/health")
def api_v1_health():
    return health_check()


# Mount static frontend if available (unified Render deployment)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "dist")
if not os.path.exists(frontend_dist):
    frontend_dist = os.path.join(os.getcwd(), "web", "dist")

if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)

