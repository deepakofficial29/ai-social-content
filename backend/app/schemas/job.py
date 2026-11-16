"""Pydantic schemas for processing jobs."""

from typing import Literal, Optional

from pydantic import BaseModel

JobStatus = Literal["queued", "processing", "completed", "failed"]


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    asset_id: Optional[str] = None
    collection_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
