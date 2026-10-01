from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class DisputeRequest(BaseModel):
  candidate_id: str
  response_id: str
  evidence: str | None = None

@router.post("/")
async def create_dispute(req: DisputeRequest):
  # Example: store dispute in a database later
  return {
    "dispute_id": "D-1001",
    "status": "Pending Review",
    "message": "Recruiter has been notified."
  }
