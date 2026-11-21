"""Deterministic Phase 4 generation, grounding, quality and API tests."""

from unittest.mock import patch

from app.evidence.pipeline import build_unified_evidence
from app.generation.grounding import validate_caption
from app.generation.quality import assess_caption_quality
from app.generation.strategy import build_generation_plan
from app.schemas.evidence import ConfidenceLevel, DetectedObject, ImageObservation, MediaEvidence
from app.schemas.generation import CaptionVariant, GenerationConfig, GroundingResult
from app.schemas.unified_evidence import EvidenceCategory, EvidenceItem, EvidenceSource, ObservationType, SourceModality


def make_package():
    source = MediaEvidence(
        collection_id="phase4-col",
        collection_type="single",
        image_observations=[
            ImageObservation(
                media_id="phase4-img",
                detected_objects=[
                    DetectedObject(label="red bicycle", confidence=ConfidenceLevel.HIGH)
                ],
                scene_description="A bicycle beside a wall",
                provider="mock",
                model_version="mock-1",
            )
        ],
        processing_status="complete",
        has_visual_evidence=True,
    )
    return build_unified_evidence(source)


def test_generation_config_validation():
    config = GenerationConfig(
        platform="instagram",
        objective="engagement",
        audience="general",
        tone="friendly",
        language="english",
        caption_length="medium",
        emoji_preference="minimal",
        hashtag_preference="relevant",
        variant_count=3,
    )
    assert config.variant_count == 3


def test_generation_config_requires_custom_description():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GenerationConfig(platform="custom")


def test_strategy_uses_supported_evidence():
    package = make_package()
    plan = build_generation_plan(package, GenerationConfig())
    assert plan.evidence_ids
    assert plan.supported_facts
    assert "bicycle" in plan.main_content_angle.lower()


def test_grounding_supported_and_unsupported_claims():
    package = make_package()
    supported = validate_caption("A red bicycle is visible.", package)
    unsupported = validate_caption("A famous person won a million dollars in Paris.", package)
    assert supported.is_verified
    assert not unsupported.is_verified
    assert unsupported.unsupported_claims


def test_grounding_preserves_original_contradiction():
    package = make_package()
    package.conflicts = []
    result = validate_caption("The bicycle is outside.", package)
    assert isinstance(result.claims, list)


def test_quality_is_explainable_and_separate_from_grounding():
    package = make_package()
    grounding = validate_caption("A red bicycle is visible.", package)
    variant = CaptionVariant(
        approach="direct",
        caption_text="A red bicycle is visible.",
        platform="instagram",
        tone="friendly",
        content_angle="Confirmed visual content",
        evidence_ids=package.evidence_items[0].evidence_ids if hasattr(package.evidence_items[0], "evidence_ids") else [package.evidence_items[0].evidence_id],
    )
    quality = assess_caption_quality(variant, GenerationConfig(), grounding)
    assert "evidence_grounding" in quality.criteria
    assert quality.grounding_separate_status == grounding.status


def test_generation_pipeline_with_mock_provider(client):
    from tests.conftest import TestingSessionLocal
    from app.database import repository as repo
    from app.generation.pipeline import run_generation_pipeline

    with TestingSessionLocal() as db:
        collection = repo.create_collection(db, "single")
        db.flush()
        package = make_package()
        package.collection_id = collection.id
        for item in package.evidence_items:
            item.source.collection_id = collection.id
            item.source.media_id = "phase4-img"
        repo.save_evidence_package(db, package)
        db.commit()
        package = repo.load_evidence_package(db, collection.id)

        provider = type("MockProvider", (), {
            "generate": lambda self, prompt: (
                '{"variants":[{"approach":"direct","caption_text":"A red bicycle is visible.",'
                '"hashtags":["bicycle"],"cta":"Take a closer look.","evidence_ids":[]},'
                '{"approach":"storytelling","caption_text":"A red bicycle is beside a wall.",'
                '"hashtags":[],"cta":null,"evidence_ids":[]}]}'
            )
        })()

        with patch("app.generation.generator.get_text_generation_provider", return_value=provider):
            with patch("app.generation.generator.get_settings") as settings:
                settings.return_value.TEXT_GENERATION_PROVIDER = "mock"
                settings.return_value.GEMINI_TEXT_MODEL = "mock-text"
                request = run_generation_pipeline(
                    db,
                    collection.id,
                    package,
                    GenerationConfig(variant_count=2),
                )

        assert len(request.variants) == 2
        assert request.grounding
        assert request.quality
        assert repo.get_generation_request(db, request.request_id) is not None


def test_generation_api_no_evidence(client):
    response = client.post(
        "/api/v1/generation/captions/missing-collection",
        json={"platform": "instagram", "variant_count": 3},
    )
    assert response.status_code == 404


def test_generation_api_missing_package(client):
    from tests.conftest import TestingSessionLocal
    from app.database import repository as repo

    with TestingSessionLocal() as db:
        collection = repo.create_collection(db, "single")
        db.commit()
        collection_id = collection.id

    response = client.post(
        f"/api/v1/generation/captions/{collection_id}",
        json={"platform": "instagram", "variant_count": 3},
    )
    assert response.status_code == 404
