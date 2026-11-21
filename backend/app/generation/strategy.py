"""Build a grounded content generation plan."""

from app.schemas.generation import GenerationConfig, GenerationPlan
from app.schemas.unified_evidence import EvidenceConflict, ObservationType, UnifiedMediaEvidence


def build_generation_plan(
    package: UnifiedMediaEvidence,
    config: GenerationConfig,
) -> GenerationPlan:
    direct = [
        item for item in package.evidence_items
        if item.observation_type == ObservationType.DIRECT_OBSERVATION
    ]
    interpretations = [
        item for item in package.evidence_items
        if item.observation_type == ObservationType.INTERPRETATION
    ]
    supported_facts = [
        f"{item.category.value}: {item.value}" for item in direct
    ]
    evidence_ids = list(dict.fromkeys(item.evidence_id for item in direct))

    subjects = [item.value for item in direct if item.category.value in {"object", "person"}]
    visual_context = [item.value for item in direct if item.category.value not in {"speech", "text_ocr"}]
    main_angle = (
        f"Present the confirmed media content around {', '.join(subjects[:3])}"
        if subjects
        else "Present only the directly supported context from the media"
    )
    key_message = package.content_summary.overall_description if package.content_summary else (
        "; ".join(supported_facts[:5]) if supported_facts else "No confirmed factual summary is available."
    )

    prohibited_claims = [
        item.value for item in interpretations
    ] + [
        conflict.description for conflict in package.conflicts
    ] + [
        item.value for item in package.evidence_items if item.uncertainty_note
    ]
    prohibited_claims = list(dict.fromkeys(prohibited_claims))

    structure = ["Lead with a confirmed observation"]
    if visual_context:
        structure.append("Add only relevant directly supported context")
    if package.transcription_evidence_ids:
        structure.append("Reference transcript excerpts only as quoted or clearly attributed speech")
    if config.cta_enabled:
        structure.append("Finish with a concise, factual CTA")

    return GenerationPlan(
        main_content_angle=main_angle,
        key_message=key_message,
        audience_relevance=f"Adapt the language and emphasis for {config.audience.value.replace('_', ' ')}.",
        recommended_structure=structure,
        tone_instructions=(
            f"Use a {config.tone.value.replace('_', ' ')} tone"
            + (f" ({config.custom_tone_description})" if config.custom_tone_description else "")
            + f", in {config.language.value.replace('_', ' ')}."
        ),
        platform_considerations=[
            f"Follow concise, native formatting conventions for {config.platform.value}.",
            "Keep factual claims tied to evidence IDs.",
            "Avoid platform rules or character limits unless externally verified.",
        ],
        supported_facts=supported_facts,
        evidence_ids=evidence_ids,
        prohibited_claims=prohibited_claims,
    )
