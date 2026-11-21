"""Evidence quality assessment and grounded content summary."""

from typing import Iterable, List

from app.schemas.evidence import MediaEvidence
from app.schemas.unified_evidence import (
    ContentSummary,
    EvidenceCategory,
    EvidenceConflict,
    EvidenceItem,
    EvidenceQualityDimensions,
    EvidenceQualityStatus,
    ObservationType,
)


def assess_quality(
    source: MediaEvidence,
    items: Iterable[EvidenceItem],
    conflicts: Iterable[EvidenceConflict],
    duplicate_relationship_count: int = 0,
) -> EvidenceQualityDimensions:
    evidence_items = list(items)
    conflicts = list(conflicts)

    direct_items = [i for i in evidence_items if i.observation_type == ObservationType.DIRECT_OBSERVATION]
    uncertain_items = [i for i in evidence_items if i.uncertainty_note]
    missing_modalities: List[str] = []
    if source.collection_type in {"single", "carousel", "multi"} and not source.image_observations:
        missing_modalities.append("image")
    if source.collection_type == "video" and not source.video_observation:
        missing_modalities.append("video")
    if source.collection_type in {"video", "audio"} and not source.transcription:
        missing_modalities.append("audio_transcription")
    if source.collection_type in {"video", "audio"} and not source.audio_observation:
        missing_modalities.append("audio_understanding")

    if evidence_items and direct_items:
        source_availability = "ok" if source.processing_status == "complete" else "partial"
        observation_completeness = "ok" if len(direct_items) >= 3 else "partial"
    elif evidence_items:
        source_availability = "partial"
        observation_completeness = "partial"
    else:
        source_availability = "missing"
        observation_completeness = "missing"

    timestamped = [i for i in evidence_items if i.source.video_start_seconds is not None or i.source.audio_start_seconds is not None]
    timestamp_validity = "ok" if source.collection_type in {"video", "audio"} and timestamped else "not_applicable"
    if source.collection_type in {"video", "audio"} and evidence_items and not timestamped:
        timestamp_validity = "partial"

    provenance_complete = all(i.source.media_id and i.source.collection_id and i.source.media_type for i in evidence_items)
    provenance_completeness = "ok" if evidence_items and provenance_complete else ("partial" if evidence_items else "missing")

    if conflicts:
        agreement = "conflict"
        status = EvidenceQualityStatus.REQUIRES_REVIEW
    elif uncertain_items:
        agreement = "not_applicable"
        status = EvidenceQualityStatus.PARTIALLY_COMPLETE
    elif evidence_items and direct_items:
        agreement = "agreement" if len({i.source.modality.value for i in evidence_items}) > 1 else "not_applicable"
        status = EvidenceQualityStatus.COMPLETE
    else:
        agreement = "not_applicable"
        status = EvidenceQualityStatus.INSUFFICIENT_EVIDENCE

    if source.processing_status == "failed" or source.processing_errors:
        status = EvidenceQualityStatus.PROCESSING_FAILED if not evidence_items else EvidenceQualityStatus.PARTIALLY_COMPLETE

    return EvidenceQualityDimensions(
        source_availability=source_availability,
        observation_completeness=observation_completeness,
        timestamp_validity=timestamp_validity,
        provenance_completeness=provenance_completeness,
        cross_modal_agreement=agreement,
        has_duplicates=duplicate_relationship_count > 0,
        has_unresolved_contradictions=bool(conflicts),
        has_processing_warnings=bool(source.processing_errors),
        missing_modalities=missing_modalities,
        overall_status=status,
    )


def build_grounded_summary(
    items: Iterable[EvidenceItem],
    conflicts: Iterable[EvidenceConflict],
) -> ContentSummary:
    evidence_items = list(items)
    direct = [i for i in evidence_items if i.observation_type == ObservationType.DIRECT_OBSERVATION]
    interpretations = [i for i in evidence_items if i.observation_type == ObservationType.INTERPRETATION]
    uncertain = [i for i in evidence_items if i.uncertainty_note]

    def values(category: EvidenceCategory, only_direct: bool = True) -> List[str]:
        pool = direct if only_direct else evidence_items
        return list(dict.fromkeys(i.value.strip() for i in pool if i.category == category and i.value.strip()))

    subjects = values(EvidenceCategory.OBJECT) + values(EvidenceCategory.PERSON)
    activities = values(EvidenceCategory.ACTIVITY)
    environments = values(EvidenceCategory.ENVIRONMENT)
    visible_text = values(EvidenceCategory.TEXT_OCR)
    spoken = values(EvidenceCategory.SPEECH)
    background = values(EvidenceCategory.ENVIRONMENTAL_SOUND) + values(EvidenceCategory.MUSIC)
    event_items = [i for i in direct if i.category == EvidenceCategory.EVENT]
    events = list(dict.fromkeys(i.value.strip() for i in event_items))

    visual_details = values(EvidenceCategory.VISUAL_ATTRIBUTE)
    interpretations_text = list(dict.fromkeys(i.value.strip() for i in interpretations))
    uncertain_text = list(dict.fromkeys(
        f"{i.value}: {i.uncertainty_note}" for i in uncertain
    ))

    missing = []
    if not subjects:
        missing.append("Main subjects could not be confirmed.")
    if not activities:
        missing.append("No activity was directly confirmed.")
    if not environments:
        missing.append("The environment or setting was not directly confirmed.")

    conflict_text = [c.description for c in conflicts]
    uncertain_text.extend(conflict_text)

    basis = list(dict.fromkeys(i.evidence_id for i in evidence_items))
    description_parts = []
    if subjects:
        description_parts.append("Confirmed subjects: " + ", ".join(subjects))
    if activities:
        description_parts.append("Confirmed activities: " + ", ".join(activities))
    if environments:
        description_parts.append("Observed setting: " + ", ".join(environments))
    if visible_text:
        description_parts.append("Visible text: " + ", ".join(visible_text))
    overall = ". ".join(description_parts) + "." if description_parts else "No confirmed observations are available."

    return ContentSummary(
        overall_description=overall,
        main_subjects=subjects,
        main_activities=activities,
        environment_and_setting=", ".join(environments) if environments else None,
        important_visual_details=visual_details,
        spoken_content=". ".join(spoken) if spoken else None,
        background_audio=", ".join(background) if background else None,
        visible_text=visible_text,
        key_events_sequence=events,
        uncertain_details=uncertain_text,
        interpretation_notes=interpretations_text,
        evidence_basis=basis,
    )
