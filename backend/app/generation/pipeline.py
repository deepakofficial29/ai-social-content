"""Orchestrate Phase 4 strategy, generation, grounding, quality and persistence."""

from sqlalchemy.orm import Session

from app.database import repository as repo
from app.generation.generator import generate_variants
from app.generation.grounding import correct_supported_caption, validate_caption
from app.generation.quality import assess_caption_quality
from app.generation.strategy import build_generation_plan
from app.schemas.generation import GenerationConfig, GenerationRequest
from app.schemas.unified_evidence import UnifiedMediaEvidence


def run_generation_pipeline(
    db: Session,
    collection_id: str,
    package: UnifiedMediaEvidence,
    config: GenerationConfig,
) -> GenerationRequest:
    plan = build_generation_plan(package, config)
    variants, provider, model_id, warnings = generate_variants(package, config, plan)

    grounding_by_variant = {}
    quality_by_variant = {}
    for variant in variants:
        original_grounding = validate_caption(variant.caption_text, package)
        correction_attempted = False
        corrected_caption = None
        if not original_grounding.is_verified:
            correction_attempted, corrected_caption = correct_supported_caption(
                original_grounding,
                variant.caption_text,
            )
            if corrected_caption:
                revalidated = validate_caption(corrected_caption, package)
                original_grounding.status = revalidated.status
                original_grounding.is_verified = revalidated.is_verified
                original_grounding.claims = revalidated.claims
                original_grounding.corrected_caption = corrected_caption
            else:
                original_grounding.corrected_caption = None
        original_grounding.correction_attempted = correction_attempted
        grounding_by_variant[variant.variant_id] = original_grounding
        quality_by_variant[variant.variant_id] = assess_caption_quality(
            variant,
            config,
            original_grounding,
        )

    package_row = repo.get_evidence_package(db, collection_id)
    request = GenerationRequest(
        collection_id=collection_id,
        evidence_package_id=package.package_id,
        evidence_package_version=package_row.package_version if package_row else 1,
        config=config,
        plan=plan,
        variants=variants,
        grounding=grounding_by_variant,
        quality=quality_by_variant,
        provider=provider,
        model_id=model_id,
        status="complete",
        warnings=warnings,
    )
    repo.save_generation_config(db, collection_id, config)
    repo.save_generation_request(db, request)
    db.commit()
    return request
