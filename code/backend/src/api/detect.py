# app/api/detect.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.audio_jobs import (
    QueueFull,
    enqueue_audio_job,
    get_job,
)
from src.services.text_analyzer import analyze_text
from src.services.audio_analyzer import analyze_audio


router = APIRouter()

# ---------------------------
# Text Request Models
# ---------------------------
# ---------------------------
# Text Request Models
# ---------------------------
class TextRequest(BaseModel):
  text: str = Field(..., example="The quick brown fox jumps over the lazy dog")

# ---------------------------
# Audio Result Models
# ---------------------------
class BranchAResult(BaseModel):
    score: float
    metadata: Dict[str, Any]

class BranchBResult(BaseModel):
    prob: float
    wins: List[float]
    duration_sec: float

class CombinedResult(BaseModel):
    score: float
    synthetic_prob: float
    reading_likelihood: float
    risk_label: str

class AudioDetectionResult(BaseModel):
    branch_a: BranchAResult
    branch_b: BranchBResult
    combined: CombinedResult


class AudioJobStatus(BaseModel):
    job_id: str
    status: str
    submitted_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[AudioDetectionResult] = None
    error: Optional[str] = None

# ---------------------------
# Text Result Model
# ---------------------------
class TextDetectionResult(BaseModel):
    score: float
    labels: Dict[str, float]
    metadata: Dict[str, Any]


# ---------------------------
# Text Endpoint
# ---------------------------
@router.post("/text", response_model=TextDetectionResult, summary="Detect text authenticity")
def detect_text(req: TextRequest):
  """Analyze a block of text and return an authenticity score and per-label confidences.

  - Returns 400 when input text is empty.
  """
  if not req.text or not req.text.strip():
      raise HTTPException(status_code=400, detail="Invalid input: text cannot be empty.")
  result = analyze_text(req.text)
  normalized = _normalize_result(result)
  return normalized


# ---------------------------
# Audio Endpoint
# ---------------------------
@router.post("/audio", response_model=AudioDetectionResult)
def detect_audio(file: UploadFile = File(...)):
    if file.content_type not in ["audio/wav", "audio/mpeg"]:
        raise HTTPException(status_code=415, detail="Unsupported file type.")
    return analyze_audio(file)


@router.post(
    "/audio/async",
    response_model=AudioJobStatus,
    summary="Queue audio detection without blocking the request",
    status_code=202,
)
async def detect_audio_async(file: UploadFile = File(...)):
    if file.content_type not in ["audio/wav", "audio/mpeg"]:
        raise HTTPException(status_code=415, detail="Unsupported file type.")
    try:
        job = await enqueue_audio_job(file)
    except QueueFull:
        raise HTTPException(status_code=429, detail="Audio queue is full, try again soon.")
    return job.serialize()


@router.get(
    "/audio/async/{job_id}",
    response_model=AudioJobStatus,
    summary="Poll status/result for an async audio job",
)
async def get_audio_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.serialize()
# ---------------------------
# Normalization helper (kept for TEXT ONLY)
# ---------------------------
def _normalize_result(result: Any) -> Dict[str, Any]:
    """
    Normalize text analyzer output into the standard structure:
        { "score": float, "labels": {label: confidence}, "metadata": {...} }
    Normalize text analyzer output into the standard structure:
        { "score": float, "labels": {label: confidence}, "metadata": {...} }
    """

    # If Pydantic model

    # If Pydantic model
    try:
        from pydantic import BaseModel as _BM
        if isinstance(result, _BM):
            result = result.dict()
    except Exception:
        pass

    if not isinstance(result, dict):
        return {"score": 0.0, "labels": {}, "metadata": {"raw": result}}

    # Already correct structure
    # Already correct structure
    if "score" in result and "labels" in result:
        return {
            "score": float(result.get("score") or 0.0),
            "labels": {k: float(v) for k, v in (result.get("labels") or {}).items()},
            "metadata": result.get("metadata") or {},
        }

    # Legacy single label
    # Legacy single label
    if "confidence" in result and "label" in result:
        labels = {str(result["label"]): float(result["confidence"])}
        metadata = {k: v for k, v in result.items() if k not in ["confidence", "label"]}
        return {
            "score": float(result["confidence"]),
            "labels": labels,
            "metadata": metadata,
        }
        labels = {str(result["label"]): float(result["confidence"])}
        metadata = {k: v for k, v in result.items() if k not in ["confidence", "label"]}
        return {
            "score": float(result["confidence"]),
            "labels": labels,
            "metadata": metadata,
        }

    # List of label objects
    if isinstance(result.get("labels"), list):
    # List of label objects
    if isinstance(result.get("labels"), list):
        labels = {}
        for item in result["labels"]:
            lbl = item.get("label")
            conf = item.get("confidence")
            if lbl is not None and conf is not None:
                labels[str(lbl)] = float(conf)

        score = float(result.get("score") or max(labels.values(), default=0.0))
        metadata = {k: v for k, v in result.items() if k not in ["labels", "score"]}

        return {
            "score": score,
            "labels": labels,
            "metadata": metadata,
        }
        for item in result["labels"]:
            lbl = item.get("label")
            conf = item.get("confidence")
            if lbl is not None and conf is not None:
                labels[str(lbl)] = float(conf)

        score = float(result.get("score") or max(labels.values(), default=0.0))
        metadata = {k: v for k, v in result.items() if k not in ["labels", "score"]}

        return {
            "score": score,
            "labels": labels,
            "metadata": metadata,
        }

    # Fallback
    return {
        "score": float(result.get("confidence", 0.0)),
        "labels": {},
        "metadata": {"raw": result},
    }
