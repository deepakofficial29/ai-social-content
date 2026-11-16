"""Job status endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.exceptions import JobNotFoundError
from app.database import repository as repo
from app.schemas.common import APIResponse
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=APIResponse[JobResponse])
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Return the current status of a processing job."""
    job = repo.get_job(db, job_id)
    if not job:
        raise JobNotFoundError(f"Job '{job_id}' not found.")
    return APIResponse.ok(
        "Job retrieved",
        data=JobResponse(
            job_id=job.id,
            status=job.status,
            asset_id=job.asset_id,
            collection_id=job.collection_id,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
        ),
    )
