"""
Lightweight in-process audio job queue.

Provides enqueue + status APIs backed by an asyncio.Queue and a single
background worker task. Keeps memory footprint low by:
  - Writing uploads to a temp file instead of holding bytes for all jobs.
  - Reusing the existing audio analyzers in a threadpool (no extra models).

The worker is started on FastAPI startup and stopped on shutdown.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import UploadFile

from src.services.audio_analyzer import analyze_audio_bytes

# Queue/backlog size safeguard (override via env AUDIO_QUEUE_MAX)
DEFAULT_MAX_QUEUE = int(os.getenv("AUDIO_QUEUE_MAX", "8"))

# Internal state
_job_queue: Optional[asyncio.Queue] = None
_jobs: Dict[str, "AudioJob"] = {}
_worker_task: Optional[asyncio.Task] = None


class QueueFull(Exception):
    """Raised when enqueue is attempted on a full queue."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AudioJob:
    job_id: str
    status: str  # queued | processing | done | error
    submitted_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    tmp_path: Optional[Path] = None

    def serialize(self) -> Dict:
        """Convert to JSON-ready dict."""
        data = asdict(self)
        for key in ("submitted_at", "started_at", "finished_at"):
            ts = data.get(key)
            if ts is not None:
                data[key] = ts.isoformat()
        # Do not leak server paths
        data.pop("tmp_path", None)
        return data


def _ensure_queue(maxsize: int = DEFAULT_MAX_QUEUE) -> asyncio.Queue:
    global _job_queue
    if _job_queue is None:
        _job_queue = asyncio.Queue(maxsize=maxsize)
    return _job_queue


def _cleanup_file(job: AudioJob) -> None:
    try:
        if job.tmp_path and job.tmp_path.exists():
            job.tmp_path.unlink()
    except Exception:
        # Best-effort cleanup; do not crash worker
        pass
    job.tmp_path = None


async def _save_upload_to_tmp(upload: UploadFile) -> Path:
    """Stream UploadFile to a temp file to keep memory bounded."""
    suffix = Path(upload.filename or "audio").suffix or ".bin"
    fd, tmp_name = tempfile.mkstemp(prefix="audiojob_", suffix=suffix)
    path = Path(tmp_name)
    with os.fdopen(fd, "wb") as fh:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
    await upload.close()
    return path


async def enqueue_audio_job(upload: UploadFile) -> AudioJob:
    """Persist the upload, create a job, and enqueue it."""
    queue = _ensure_queue()
    if queue.full():
        raise QueueFull("audio queue is full")

    tmp_path = await _save_upload_to_tmp(upload)
    job = AudioJob(
        job_id=uuid.uuid4().hex,
        status="queued",
        submitted_at=_utcnow(),
        tmp_path=tmp_path,
    )
    _jobs[job.job_id] = job
    await queue.put(job)
    return job


def get_job(job_id: str) -> Optional[AudioJob]:
    return _jobs.get(job_id)


async def _process_job(job: AudioJob) -> None:
    """Run heavy audio analysis in a threadpool to avoid blocking the loop."""
    loop = asyncio.get_running_loop()
    if not job.tmp_path:
        raise RuntimeError("missing audio payload")

    audio_bytes = await loop.run_in_executor(None, job.tmp_path.read_bytes)
    result = await loop.run_in_executor(None, analyze_audio_bytes, audio_bytes)
    job.result = result


async def _worker() -> None:
    queue = _ensure_queue()
    while True:
        job: AudioJob = await queue.get()
        job.status = "processing"
        job.started_at = _utcnow()
        try:
            await _process_job(job)
            job.status = "done"
            job.finished_at = _utcnow()
        except Exception as exc:  # noqa: BLE001 broad is fine for job accounting
            job.status = "error"
            job.error = str(exc)
            job.finished_at = _utcnow()
        finally:
            _cleanup_file(job)
            queue.task_done()


async def start_worker(maxsize: int = DEFAULT_MAX_QUEUE) -> None:
    """Start the background worker if not already running."""
    global _worker_task
    _ensure_queue(maxsize=maxsize)
    if _worker_task is None or _worker_task.done():
        loop = asyncio.get_running_loop()
        _worker_task = loop.create_task(_worker())


async def stop_worker() -> None:
    """Cancel the worker task on shutdown."""
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
