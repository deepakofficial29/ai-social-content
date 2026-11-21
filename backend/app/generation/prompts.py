"""Prompt construction helpers for grounded caption generation."""

import json

from app.schemas.generation import GenerationConfig, GenerationPlan
from app.schemas.unified_evidence import UnifiedMediaEvidence


def build_caption_prompt(
    package: UnifiedMediaEvidence,
    plan: GenerationPlan,
    config: GenerationConfig,
) -> str:
    evidence = [
        {
            "evidence_id": item.evidence_id,
            "category": item.category.value,
            "observation_type": item.observation_type.value,
            "value": item.value,
            "uncertainty": item.uncertainty_note,
            "source": item.source.model_dump(mode="json"),
        }
        for item in package.evidence_items
    ]
    allowed = {
        "platform": config.platform.value,
        "objective": config.objective.value,
        "audience": config.audience.value,
        "tone": config.tone.value,
        "language": config.language.value,
        "caption_length": config.caption_length.value,
        "emoji_preference": config.emoji_preference.value,
        "hashtag_preference": config.hashtag_preference.value,
        "cta_enabled": config.cta_enabled,
        "brand_voice": config.brand_voice_description,
        "brand_name": config.brand_name,
        "keywords_to_include": config.keywords_to_include,
        "words_or_claims_to_avoid": config.words_or_claims_to_avoid,
        "additional_instructions": config.additional_instructions,
        "custom_platform": config.custom_platform_description,
        "custom_objective": config.custom_objective_description,
        "custom_audience": config.custom_audience_description,
        "custom_tone": config.custom_tone_description,
        "custom_language": config.custom_language_description,
    }
    return (
        "Create grounded social captions using ONLY this evidence package. "
        "Do not invent people, identities, locations, objects, actions, events, numbers, statistics, "
        "products, emotional claims, or context absent from the evidence.\n\n"
        "Every factual claim must be attributable to evidence IDs. Preserve uncertainty and contradictions.\n"
        "Do not resolve conflicts by selecting the highest-confidence source.\n"
        "Return ONLY valid JSON with this shape:\n"
        '{\"variants\":[{\"approach\":\"direct|storytelling|engagement\",\"caption_text\":\"...\",'
        '\"hashtags\":[\"...\"],\"cta\":\"... or null\",\"evidence_ids\":[\"...\"]}]}\n\n'
        f"Evidence package:\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
        f"Generation plan:\n{json.dumps(plan.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
        f"User configuration:\n{json.dumps(allowed, ensure_ascii=False)}\n\n"
        f"Generate exactly {config.variant_count} variants."
    )
