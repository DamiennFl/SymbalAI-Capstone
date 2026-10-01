# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api import detect, disputes, internal
import logging
from src.services.audio_jobs import start_worker as start_audio_worker, stop_worker as stop_audio_worker

# Configure logging to skip health check endpoints
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter out health check endpoint logs
        message = record.getMessage()
        health_paths = ["/health", "/liveness", "/readiness"]
        return not any(path in message for path in health_paths)

# Apply filter to uvicorn/granian access logs
for logger_name in ["uvicorn.access", "granian.access", "uvicorn", "granian"]:
    logger = logging.getLogger(logger_name)
    logger.addFilter(HealthCheckFilter())

# Customize the docs paths so Swagger is at /swagger and OpenAPI JSON at /openapi.json
app = FastAPI(
  title="Symbal AI Authenticity Detection API",
  description="REST microservice for text/audio authenticity scoring and dispute handling",
  version="1.0.0",
  docs_url="/docs",
  redoc_url="/redoc",
  openapi_url="/openapi.json",
  swagger_ui_parameters={
    "defaultModelsExpandDepth": -1,  # hide models by default
    "displayRequestDuration": True,
  },
)

# ------------------------------------------------------
# CORS CONFIGURATION
# ------------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # <-- allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # <-- allow all HTTP methods
    allow_headers=["*"],            # <-- allow all headers
)
# ------------------------------------------------------

# ------------------------------------------------------
# CORS CONFIGURATION
# ------------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # <-- allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # <-- allow all HTTP methods
    allow_headers=["*"],            # <-- allow all headers
)
# ------------------------------------------------------

# Include routers
app.include_router(detect.router, prefix="/detect", tags=["Detection"])
app.include_router(disputes.router, prefix="/disputes", tags=["Disputes"])
app.include_router(internal.router, prefix="/internal", tags=["Internal"])


@app.on_event("startup")
async def _start_audio_queue():
    # Uses AUDIO_QUEUE_MAX env var if set
    await start_audio_worker()


@app.on_event("shutdown")
async def _stop_audio_queue():
    await stop_audio_worker()

@app.get("/health", tags=["Health"])
def health_check():
  return {"status": "ok", "message": "AI Cheat Detector API running"}

@app.get("/liveness", tags=["Health"])
def liveness_probe():
  """Liveness probe for Kubernetes/container orchestration."""
  return {"status": "ok"}

@app.get("/readiness", tags=["Health"])
def readiness_probe():
  """Readiness probe - checks if models are loaded and service is ready to handle requests"""
  try:
    # Check if Branch A model is loaded
    from src.services.branch_a_reader import MODEL as whisper_model
    if whisper_model is None:
      return JSONResponse(content={"status": "not ready", "reason": "Whisper model not loaded"}, status_code=503)
    
    # Check if Branch B model is loaded
    from src.services.audio_analyzer import BRANCH_B_MODEL
    if BRANCH_B_MODEL is None:
      return JSONResponse(content={"status": "not ready", "reason": "Branch B model not loaded"}, status_code=503)
    
    return JSONResponse(content={"status": "ready"}, status_code=200)
  except Exception as e:
    return JSONResponse(content={"status": "not ready", "reason": str(e)}, status_code=503)
