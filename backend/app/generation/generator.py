"""Platform-aware grounded caption variant generation."""

import json
from typing import List

from app.core.config import get_settings
from app.providers.registry import get_text_generation_provider
from app.schemas.generation import CaptionVariant, GenerationConfig, GenerationPlan
from app.schemas.unified_evidence import UnifiedMediaEvidence
from app.generation.prompts import build_caption_prompt


def _grounded_fallback(package: UnifiedMediaEvidence, config: GenerationConfig) -> str:
    subjects = []
    activities = []
    direct = [i for i in package.evidence_items if i.observation_type.value == "direct_observation"]
    for item in direct:
        if item.category.value in {"object", "person"}:
            subjects.append(item.value)
        if item.category.value == "activity":
            activities.append(item.value)
    parts = []
    if subjects:
        parts.append("Observed: " + ", ".join(dict.fromkeys(subjects)))
    if activities:
        parts.append("Activities: " + ", ".join(dict.fromkeys(activities)))
    if not parts:
        return "No confirmed visual or audio facts are available from this media."
    return ". ".join(parts) + "."


def _parse_variants(raw: str, config: GenerationConfig) -> List[dict]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(text)
    variants = data.get("variants", []) if isinstance(data, dict) else data
    if not isinstance(variants, list):
        raise ValueError("Text provider returned no variant list")
    return variants[: config.variant_count]


def generate_variants(
    package: UnifiedMediaEvidence,
    config: GenerationConfig,
    plan: GenerationPlan,
) -> tuple[List[CaptionVariant], str, str, List[str]]:
    prompt = build_caption_prompt(package, plan, config)
    provider_name = get_settings().TEXT_GENERATION_PROVIDER
    provider = get_text_generation_provider(provider_name)
    model_id = get_settings().GEMINI_TEXT_MODEL if provider_name.startswith("gemini") else provider_name
    warnings: List[str] = []

    raw_variants = None
    try:
        raw = provider.generate(prompt)
        raw_variants = _parse_variants(raw, config)
    except Exception as exc:
        warnings.append(f"{provider_name} generation failed or returned invalid output: {exc}")

    approaches = ["direct and concise", "storytelling", "engagement-oriented"]
    variants: List[CaptionVariant] = []
    source_ids = plan.evidence_ids
    fallback = _grounded_fallback(package, config)

    supplied = raw_variants or []
    while len(supplied) < config.variant_count:
        supplied.append({
            "approach": approaches[len(supplied) % len(approaches)],
            "caption_text": fallback,
            "hashtags": [],
            "cta": None,
            "evidence_ids": source_ids,
        })

    for index, item in enumerate(supplied[: config.variant_count]):
        approach = str(item.get("approach") or approaches[index % len(approaches)])
        caption = str(item.get("caption_text") or fallback).strip()
        hashtag_values = item.get("hashtags", [])
        hashtags = [
            value if str(value).startswith("#") else f"#{value}"
            for value in (hashtag_values if isinstance(hashtag_values, list) else [])
            if str(value).strip()
        ]
        evidence_ids = [
            evidence_id for evidence_id in item.get("evidence_ids", [])
            if evidence_id in {entry.evidence_id for entry in package.evidence_items}
        ]
        cta = item.get("cta") if config.cta_enabled else None
        variants.append(CaptionVariant(
            approach=approach,
            caption_text=caption,
            platform=config.platform,
            tone=config.tone,
            content_angle=plan.main_content_angle,
            hashtags=hashtags if config.hashtag_preference != "disabled" else [],
            cta=cta,
            evidence_ids=evidence_ids or source_ids,
            provider=provider_name,
            model_id=model_id,
        ))
    return variants, provider_name, model_id, warnings
