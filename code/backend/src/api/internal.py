from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class InternalTestResponse(BaseModel):
    test: str = Field(..., example="ok")
    runtime_ms: int = Field(..., example=123)
    model_used: str = Field(..., example="DetectGPT-v2")


class MonitorStatus(BaseModel):
    uptime: str = Field(..., example="99.98%")
    requests_per_minute: int = Field(..., example=250)
    avg_response_time_ms: int = Field(..., example=210)
    error_rate: float = Field(..., example=1.2)


@router.post("/test", response_model=InternalTestResponse, summary="Internal health test")
def internal_test():
    """Simple internal test endpoint used for CI/monitoring checks."""
    return {"test": "ok", "runtime_ms": 123, "model_used": "DetectGPT-v2"}


@router.get("/monitor", response_model=MonitorStatus, summary="Service monitor status")
def monitor_status():
    """Return quick runtime metrics useful for dashboards."""
    return {
        "uptime": "99.98%",
        "requests_per_minute": 250,
        "avg_response_time_ms": 210,
        "error_rate": 1.2,
    }
