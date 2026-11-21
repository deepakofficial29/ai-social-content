"""Pydantic schemas for understanding API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.schemas.evidence import ConfidenceLevel, MediaEvidence


class UnderstandingJobResponse(BaseModel):
    """Response when an understanding job is started."""

    collection_id: str
    status: str
    message: str


class EvidenceResponse(BaseModel):
    """API response wrapper for MediaEvidence."""

    collection_id: str
    collection_type: str
    processing_status: str
    processed_at: Optional[datetime] = None
    has_visual_evidence: bool
    has_audio_evidence: bool
    has_transcription: bool
    overall_confidence: ConfidenceLevel
    providers_used: List[str]
    processing_errors: List[str]
    evidence: Dict[str, Any]  # full MediaEvidence as dict

    @classmethod
    def from_evidence(cls, ev: MediaEvidence) -> "EvidenceResponse":
        return cls(
            collection_id=ev.collection_id,
            collection_type=ev.collection_type,
            processing_status=ev.processing_status,
            processed_at=ev.processed_at,
            has_visual_evidence=ev.has_visual_evidence,
            has_audio_evidence=ev.has_audio_evidence,
            has_transcription=ev.has_transcription,
            overall_confidence=ev.overall_confidence,
            providers_used=ev.providers_used,
            processing_errors=ev.processing_errors,
            evidence=ev.model_dump(mode="json"),
        )
