"""Heuristic grounding validation for generated captions."""

import re
from typing import Iterable, List

from app.schemas.generation import (
    ClaimClassification,
    GroundingClaim,
    GroundingResult,
)
from app.schemas.unified_evidence import UnifiedMediaEvidence

_FACTUAL_HINTS = (
    "is ", "are ", "was ", "were ", "has ", "have ", "shows ", "features ",
    "located", "person", "people", "wearing", "holding", "standing", "sitting",
    "running", "walking", "at ", "from ", "with ", "contains ", "includes ",
    "million", "billion", "percent", "%", "launch", "opened", "won",
)


def _sentences(text: str) -> List[str]:
    values = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return values or ([text.strip()] if text.strip() else [])


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def validate_caption(
    caption: str,
    package: UnifiedMediaEvidence,
) -> GroundingResult:
    evidence_values = {
        item.evidence_id: _normalise(item.value)
        for item in package.evidence_items
    }
    evidence_text = " ".join(evidence_values.values())
    conflict_ids = {
        evidence_id
        for conflict in package.conflicts
        for evidence_id in conflict.conflicting_evidence_ids
    }

    claims: List[GroundingClaim] = []
    unsupported: List[str] = []
    contradicted: List[str] = []

    for sentence in _sentences(caption):
        normal = _normalise(sentence)
        if not normal:
            continue

        supporting_ids = [
            evidence_id
            for evidence_id, value in evidence_values.items()
            if value and (value in normal or normal in value)
        ]
        if not supporting_ids:
            sentence_words = set(normal.split())
            evidence_words = set(evidence_text.split())
            overlap = sentence_words & evidence_words
            if len(overlap) >= 2:
                candidates = [
                    evidence_id
                    for evidence_id, value in evidence_values.items()
                    if len(set(_normalise(value).split()) & sentence_words) >= 2
                ]
                supporting_ids.extend(dict.fromkeys(candidates))

        if any(evidence_id in conflict_ids for evidence_id in supporting_ids):
            classification = ClaimClassification.CONTRADICTED
            contradicted.append(sentence)
            explanation = "The claim overlaps evidence that is part of an unresolved contradiction."
        elif supporting_ids:
            classification = ClaimClassification.SUPPORTED
            explanation = "The claim overlaps directly retrievable evidence."
        elif any(hint in normal for hint in _FACTUAL_HINTS):
            classification = ClaimClassification.UNSUPPORTED
            unsupported.append(sentence)
            explanation = "The sentence makes a factual or contextual claim not found in the evidence package."
        else:
            classification = ClaimClassification.NON_FACTUAL
            explanation = "The sentence appears stylistic or calls for engagement rather than asserting a factual claim."

        claims.append(GroundingClaim(
            claim=sentence,
            classification=classification,
            evidence_ids=supporting_ids,
            explanation=explanation,
        ))

    is_verified = not unsupported and not contradicted
    status = "verified" if is_verified else ("contradicted" if contradicted else "unverified")
    return GroundingResult(
        status=status,
        is_verified=is_verified,
        claims=claims,
        unsupported_claims=unsupported,
        contradicted_claims=contradicted,
    )


def correct_supported_caption(
    original: GroundingResult,
    caption: str,
) -> tuple[bool, str]:
    """Remove clearly unsupported sentences and preserve verified/stylistic text."""
    if original.is_verified:
        return False, caption

    unsupported = set(original.unsupported_claims)
    contradicted = set(original.contradicted_claims)
    kept = [
        sentence for sentence in _sentences(caption)
        if sentence not in unsupported and sentence not in contradicted
    ]
    return True, " ".join(kept).strip()
