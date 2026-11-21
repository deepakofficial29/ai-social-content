"""Explainable caption quality assessment."""

from typing import Iterable

from app.schemas.generation import CaptionVariant, GenerationConfig, GroundingResult, QualityResult


def assess_caption_quality(
    variant: CaptionVariant,
    config: GenerationConfig,
    grounding: GroundingResult,
) -> QualityResult:
    text = variant.caption_text.strip()
    words = text.split()
    strengths: list[str] = []
    weaknesses: list[str] = []
    criteria: dict[str, str] = {}

    if grounding.is_verified:
        strengths.append("Caption contains no identified unsupported or contradicted claims.")
        criteria["evidence_grounding"] = "verified"
    else:
        weaknesses.append("Grounding issues remain and must be reviewed.")
        criteria["evidence_grounding"] = grounding.status

    length = config.caption_length.value
    if (length == "short" and len(words) <= 30) or (length == "medium" and len(words) <= 100) or (length == "long" and len(words) <= 220):
        strengths.append("Length is appropriate for the selected setting.")
        criteria["readability"] = "appropriate_length"
    else:
        weaknesses.append("Caption exceeds the practical word range for the selected length.")
        criteria["readability"] = "length_mismatch"

    unique_ratio = len(set(words.lower() for words in words)) / max(len(words), 1)
    if unique_ratio >= 0.65:
        strengths.append("Word repetition appears limited.")
        criteria["repetition"] = "low"
    else:
        weaknesses.append("Caption has notable repetition.")
        criteria["repetition"] = "high"

    criteria["objective_relevance"] = "configured_for_" + config.objective.value
    criteria["audience_suitability"] = "configured_for_" + config.audience.value
    criteria["platform_suitability"] = "configured_for_" + config.platform.value
    criteria["tone_consistency"] = "configured_for_" + config.tone.value
    criteria["naturalness"] = "human_review_recommended"
    criteria["hashtag_relevance"] = (
        "disabled" if config.hashtag_preference.value == "disabled"
        else ("provided" if variant.hashtags else "none")
    )
    criteria["cta_relevance"] = "enabled" if variant.cta else "disabled_or_missing"

    return QualityResult(
        grounding_separate_status=grounding.status,
        strengths=strengths,
        weaknesses=weaknesses,
        criteria=criteria,
    )
