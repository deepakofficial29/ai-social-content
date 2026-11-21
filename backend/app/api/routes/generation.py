"""Phase 4 content strategy and grounded caption generation endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.exceptions import EvidenceNotFoundError, MediaNotFoundError
from app.database import repository as repo
from app.generation.pipeline import run_generation_pipeline
from app.generation.strategy import build_generation_plan
from app.schemas.common import APIResponse
from app.schemas.generation import (
    CaptionVariant,
    GenerationConfig,
    GenerationPlan,
    GenerationRequest,
    GroundingResult,
    QualityResult,
)

router = APIRouter(prefix="/generation", tags=["generation"])


def _collection_and_package(db: Session, media_id: str):
    collection = repo.get_collection(db, media_id)
    if not collection:
        raise MediaNotFoundError(f"Collection '{media_id}' not found.")
    package = repo.load_evidence_package(db, media_id)
    if not package:
        raise EvidenceNotFoundError(
            f"No evidence package exists for collection '{media_id}'."
        )
    usable = [
        item for item in package.evidence_items
        if item.value.strip()
    ]
    if not usable:
        raise EvidenceNotFoundError(
            f"No usable evidence exists for collection '{media_id}'."
        )
    return package


@router.post("/config/{media_id}", response_model=APIResponse[GenerationConfig])
def save_config(media_id: str, config: GenerationConfig, db: Session = Depends(get_db)):
    if not repo.get_collection(db, media_id):
        raise MediaNotFoundError(f"Collection '{media_id}' not found.")
    config.media_id = media_id
    repo.save_generation_config(db, media_id, config)
    db.commit()
    return APIResponse.ok("Generation configuration saved", data=config)


@router.post("/config", response_model=APIResponse[GenerationConfig])
def save_config_without_path(config: GenerationConfig, db: Session = Depends(get_db)):
    if not config.media_id:
        raise EvidenceNotFoundError("media_id is required in the generation configuration.")
    if not repo.get_collection(db, config.media_id):
        raise MediaNotFoundError(f"Collection '{config.media_id}' not found.")
    repo.save_generation_config(db, config.media_id, config)
    db.commit()
    return APIResponse.ok("Generation configuration saved", data=config)


@router.get("/config/{media_id}", response_model=APIResponse[GenerationConfig])
def get_config(media_id: str, db: Session = Depends(get_db)):
    if not repo.get_collection(db, media_id):
        raise MediaNotFoundError(f"Collection '{media_id}' not found.")
    config = repo.get_generation_config(db, media_id)
    if not config:
        raise EvidenceNotFoundError(f"No generation configuration exists for collection '{media_id}'.")
    return APIResponse.ok("Generation configuration retrieved", data=config)


@router.get("", response_model=APIResponse[list[GenerationRequest]])
def list_generations(db: Session = Depends(get_db)):
    requests = repo.list_all_generation_requests(db)
    return APIResponse.ok("Generation history retrieved", data=requests)


@router.post("/strategy/{media_id}", response_model=APIResponse[GenerationPlan])
def create_strategy(
    media_id: str,
    config: GenerationConfig,
    db: Session = Depends(get_db),
):
    package = _collection_and_package(db, media_id)
    plan = build_generation_plan(package, config)
    return APIResponse.ok("Content strategy generated", data=plan)


@router.post("/captions/{media_id}", response_model=APIResponse[GenerationRequest])
def generate_captions(
    media_id: str,
    config: GenerationConfig,
    db: Session = Depends(get_db),
):
    package = _collection_and_package(db, media_id)
    config.media_id = media_id
    request = run_generation_pipeline(db, media_id, package, config)
    return APIResponse.ok("Caption variants generated", data=request)


@router.get("/{generation_id}", response_model=APIResponse[GenerationRequest])
def get_generation(generation_id: str, db: Session = Depends(get_db)):
    request = repo.get_generation_request(db, generation_id)
    if not request:
        raise EvidenceNotFoundError(f"Generation '{generation_id}' not found.")
    return APIResponse.ok("Generation retrieved", data=request)


@router.get("/{generation_id}/variants", response_model=APIResponse[list[CaptionVariant]])
def get_variants(generation_id: str, db: Session = Depends(get_db)):
    request = repo.get_generation_request(db, generation_id)
    if not request:
        raise EvidenceNotFoundError(f"Generation '{generation_id}' not found.")
    return APIResponse.ok("Caption variants retrieved", data=request.variants)


@router.get("/{generation_id}/quality", response_model=APIResponse[dict[str, QualityResult]])
def get_generation_quality(generation_id: str, db: Session = Depends(get_db)):
    request = repo.get_generation_request(db, generation_id)
    if not request:
        raise EvidenceNotFoundError(f"Generation '{generation_id}' not found.")
    return APIResponse.ok("Caption quality retrieved", data=request.quality)


@router.get("/{generation_id}/grounding", response_model=APIResponse[dict[str, GroundingResult]])
def get_generation_grounding(generation_id: str, db: Session = Depends(get_db)):
    request = repo.get_generation_request(db, generation_id)
    if not request:
        raise EvidenceNotFoundError(f"Generation '{generation_id}' not found.")
    return APIResponse.ok("Grounding validation retrieved", data=request.grounding)


@router.post("/{generation_id}/regenerate", response_model=APIResponse[GenerationRequest])
def regenerate(generation_id: str, db: Session = Depends(get_db)):
    previous = repo.get_generation_request(db, generation_id)
    if not previous:
        raise EvidenceNotFoundError(f"Generation '{generation_id}' not found.")
    package = repo.load_evidence_package(db, previous.collection_id)
    if not package:
        raise EvidenceNotFoundError(
            f"No evidence package exists for collection '{previous.collection_id}'."
        )
    request = run_generation_pipeline(db, previous.collection_id, package, previous.config)
    return APIResponse.ok("Caption variants regenerated", data=request)
