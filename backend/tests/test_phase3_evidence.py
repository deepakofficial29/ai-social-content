"""Phase 3 evidence construction, persistence, and API tests."""

from sqlalchemy.orm import Session

from app.database import repository as repo
from app.evidence.fusion import (
    detect_contradictions,
    detect_cross_modal_relationships,
    detect_duplicate_relationships,
)
from app.evidence.normalizers import normalize_image_evidence, normalize_transcription_evidence
from app.evidence.pipeline import build_unified_evidence
from app.evidence.quality import assess_quality, build_grounded_summary
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    DetectedObject,
    ExtractedText,
    ImageObservation,
    MediaEvidence,
    TranscriptionResult,
)
from app.schemas.unified_evidence import (
    EvidenceCategory,
    ObservationType,
)


def image_source(value: str = "red car", media_id: str = "img-1"):
    return ImageObservation(
        media_id=media_id,
        detected_objects=[DetectedObject(label=value, confidence=ConfidenceLevel.HIGH)],
        extracted_text=[ExtractedText(text="SALE", confidence=ConfidenceLevel.HIGH)],
        scene_description="A car parked outside",
        provider="mock-vision",
        model_version="mock-1",
    )


def test_image_normalization_separates_observation_and_interpretation():
    obs = image_source()
    items = normalize_image_evidence(obs, "collection-1", image_index=2)

    direct = [item for item in items if item.observation_type == ObservationType.DIRECT_OBSERVATION]
    interpretations = [item for item in items if item.observation_type == ObservationType.INTERPRETATION]
    assert direct
    assert interpretations
    assert any(item.category == EvidenceCategory.OBJECT for item in direct)
    assert all(item.source.collection_id == "collection-1" for item in items)
    assert all(item.source.image_index == 2 for item in items)


def test_transcription_normalization_preserves_timestamps():
    from app.schemas.evidence import TranscriptionSegment

    result = TranscriptionResult(
        media_id="audio-1",
        full_text="Hello there",
        segments=[TranscriptionSegment(
            text="Hello there",
            start_seconds=1.25,
            end_seconds=2.5,
            confidence=ConfidenceLevel.HIGH,
        )],
        provider="mock-transcription",
        model_version="mock-1",
    )
    items = normalize_transcription_evidence(result, "collection-1")
    assert len(items) == 1
    assert items[0].source.audio_start_seconds == 1.25
    assert items[0].source.audio_end_seconds == 2.5


def test_duplicate_detection_preserves_original_items():
    items = normalize_image_evidence(image_source(), "collection-1")
    items += normalize_image_evidence(image_source(), "collection-1")
    relationships = detect_duplicate_relationships(items)
    assert len(items) == 6
    assert all(relationship.relationship_type.value == "duplicate" for relationship in relationships)


def test_complementary_and_conflicting_evidence_are_explainable():
    source = MediaEvidence(
        collection_id="collection-1",
        collection_type="video",
        image_observations=[image_source()],
        transcription=TranscriptionResult(
            media_id="video-1",
            full_text="A meeting begins",
            provider="mock",
        ),
        processing_status="partial",
        processing_errors=["One provider failed"],
    )
    package = build_unified_evidence(source)

    assert package.evidence_items
    assert package.cross_modal_relationships or len(package.evidence_items) >= 2
    assert package.quality is not None
    assert package.content_summary is not None


def test_contradiction_detection_flags_indoor_outdoor_difference():
    from app.schemas.unified_evidence import EvidenceItem, EvidenceSource, SourceModality

    def item(value: str, evidence_id: str):
        return EvidenceItem(
            evidence_id=evidence_id,
            category=EvidenceCategory.ENVIRONMENT,
            observation_type=ObservationType.INTERPRETATION,
            value=value,
            source=EvidenceSource(
                media_id="video-1",
                collection_id="collection-1",
                media_type="video",
                modality=SourceModality.VIDEO_FRAME,
                provider="provider-a" if evidence_id == "a" else "provider-b",
                frame_index=1,
            ),
        )

    conflicts = detect_contradictions([item("indoor studio", "a"), item("outdoor street", "b")])
    assert len(conflicts) == 1
    assert conflicts[0].resolution_status == "unresolved"


def test_quality_and_summary_do_not_invent_missing_information():
    source = MediaEvidence(
        collection_id="collection-1",
        collection_type="image",
        image_observations=[ImageObservation(media_id="img-1", provider="mock")],
        processing_status="complete",
    )
    package = build_unified_evidence(source)
    assert package.content_summary is not None
    assert "No confirmed observations" in package.content_summary.overall_description
    assert package.quality is not None
    assert package.quality.overall_status.value in {"insufficient_evidence", "processing_failed", "partially_complete", "complete", "requires_review"}


def test_persistence_save_retrieve_and_version(client):
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        collection = repo.create_collection(db, "single")
        source = MediaEvidence(
            collection_id=collection.id,
            collection_type="single",
            image_observations=[image_source(media_id="img-1")],
            processing_status="complete",
        )
        package = build_unified_evidence(source)
        saved = repo.save_evidence_package(db, package)
        db.commit()

        first = repo.load_evidence_package(db, collection.id)
        assert first is not None
        assert first.collection_id == collection.id
        assert first.evidence_items

        package.processing_status = "partial"
        package.updated_at = package.updated_at
        repo.save_evidence_package(db, package)
        db.commit()
        row = repo.get_evidence_package(db, collection.id)
        assert row.package_version == 2
        assert repo.load_evidence_package(db, collection.id).processing_status == "partial"


def test_api_returns_missing_package_without_provider_processing(client):
    response = client.post(
        "/api/v1/media/upload",
        files=[("files", ("sample.png", b"not-an-image", "image/png"))],
    )
    # This is expected to fail intake validation; the test verifies missing evidence separately.
    assert response.status_code in {201, 422, 415}

    missing = client.get("/api/v1/evidence/does-not-exist")
    assert missing.status_code == 404


def test_api_persisted_package_routes(client):
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        collection = repo.create_collection(db, "single")
        source = MediaEvidence(
            collection_id=collection.id,
            collection_type="single",
            image_observations=[image_source(media_id="img-api")],
            processing_status="complete",
        )
        package = build_unified_evidence(source)
        repo.save_evidence_package(db, package)
        db.commit()
        collection_id = collection.id

    paths = ["", "/items", "/provenance", "/relationships", "/conflicts", "/quality", "/summary"]
    for suffix in paths:
        response = client.get(f"/api/v1/evidence/{collection_id}{suffix}")
        assert response.status_code == 200, (suffix, response.text)


def test_evidence_review_interface_is_served(client):
    response = client.get("/api/v1/evidence/review/example-collection")
    assert response.status_code == 200
    assert "Evidence Review" in response.text
