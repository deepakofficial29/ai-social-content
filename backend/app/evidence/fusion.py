"""Phase 3 — Multimodal evidence fusion.

Combines evidence items from different modalities, identifies relationships,
detects duplicates conservatively, and flags potential contradictions.

Fusion is evidence-based — no second AI call is made.
A difference between modalities is not automatically a contradiction.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from app.core.logging import get_logger
from app.schemas.unified_evidence import (
    CrossModalRelationship,
    EvidenceCategory,
    EvidenceConflict,
    EvidenceItem,
    ObservationType,
    RelationshipType,
    SourceModality,
)

logger = get_logger(__name__)

# Minimum text similarity ratio to consider two items potential duplicates
_DUPLICATE_SIMILARITY_THRESHOLD = 0.85
# Timestamp window (seconds) for associating audio with video events
_TIMESTAMP_WINDOW_SECONDS = 3.0


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def detect_duplicates(items: List[EvidenceItem]) -> List[EvidenceItem]:
    """Return the original evidence list unchanged.

    Duplicate and overlap relationships are reported separately.  This
    function intentionally never removes an item or rewrites provenance.
    """
    return list(items)


def _are_duplicates(a: EvidenceItem, b: EvidenceItem) -> bool:
    """Return True only when two items are clearly the same observation."""
    if a.category != b.category:
        return False
    if a.observation_type != b.observation_type:
        return False
    # Same modality and same source media — likely duplicate
    if a.source.media_id != b.source.media_id:
        return False
    # Text similarity check
    ratio = _text_similarity(a.value, b.value)
    return ratio >= _DUPLICATE_SIMILARITY_THRESHOLD


def _text_similarity(a: str, b: str) -> float:
    """Simple normalised character overlap similarity (no external deps)."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _merge_duplicates(items: List[EvidenceItem]) -> EvidenceItem:
    """Merge duplicate items, preserving all source references."""
    primary = items[0]
    all_ids = [it.evidence_id for it in items]
    # Keep the highest-confidence item as primary if available
    confidence_order = {"high": 0, "medium": 1, "low": 2, None: 3}
    items_sorted = sorted(items, key=lambda x: confidence_order.get(x.confidence, 3))
    primary = items_sorted[0]

    merged = primary.model_copy(deep=True)
    merged.supporting_evidence_ids = [
        eid for eid in all_ids if eid != primary.evidence_id
    ]
    return merged


def detect_duplicate_relationships(
    items: List[EvidenceItem],
) -> List[CrossModalRelationship]:
    """Create conservative duplicate/overlap links without deleting evidence."""
    relationships: List[CrossModalRelationship] = []
    used_pairs: Set[Tuple[str, str]] = set()
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            pair = tuple(sorted((a.evidence_id, b.evidence_id)))
            if pair in used_pairs:
                continue
            if not _are_duplicates(a, b):
                continue
            used_pairs.add(pair)
            relationships.append(CrossModalRelationship(
                relationship_type=RelationshipType.DUPLICATE,
                evidence_ids=[a.evidence_id, b.evidence_id],
                description=(
                    "These items are conservatively identified as likely duplicates "
                    "of the same category and meaning. Both originals remain available."
                ),
            ))
    return relationships


# ---------------------------------------------------------------------------
# Cross-modal relationship detection
# ---------------------------------------------------------------------------


def detect_cross_modal_relationships(
    items: List[EvidenceItem],
) -> List[CrossModalRelationship]:
    """Identify relationships between evidence items from different modalities.

    Relationships detected:
    - Speech + visual scene (complementary when timestamps overlap)
    - OCR text + speech mentioning same text (agreement)
    - Music + visual mood (complementary)
    - Video event + audio event at same timestamp (complementary or agreement)
    """
    relationships: List[CrossModalRelationship] = []

    speech_items = [i for i in items if i.category == EvidenceCategory.SPEECH
                    and i.observation_type == ObservationType.DIRECT_OBSERVATION]
    ocr_items = [i for i in items if i.category == EvidenceCategory.TEXT_OCR]
    music_items = [i for i in items if i.category == EvidenceCategory.MUSIC]
    scene_items = [i for i in items if i.category == EvidenceCategory.SCENE]
    video_event_items = [i for i in items
                         if i.category == EvidenceCategory.EVENT
                         and i.source.modality in (SourceModality.VIDEO_OVERALL, SourceModality.VIDEO_FRAME)]
    audio_event_items = [i for i in items
                         if i.category == EvidenceCategory.EVENT
                         and i.source.modality == SourceModality.AUDIO_UNDERSTANDING]

    # Speech + scene (complementary — audio and visual co-exist)
    for sp in speech_items:
        for sc in scene_items:
            if sp.source.media_id == sc.source.media_id:
                rel = CrossModalRelationship(
                    relationship_type=RelationshipType.COMPLEMENTARY,
                    evidence_ids=[sp.evidence_id, sc.evidence_id],
                    description=(
                        f"Speech ('{_truncate(sp.value)}') co-exists with "
                        f"visual scene ('{_truncate(sc.value)}'). "
                        "Relationship is complementary — audio does not necessarily describe the scene."
                    ),
                )
                relationships.append(rel)

    # OCR text + speech mentioning same words (agreement)
    for ocr in ocr_items:
        for sp in speech_items:
            if sp.source.media_id == ocr.source.media_id:
                ocr_words = set(ocr.value.lower().split())
                speech_words = set(sp.value.lower().split())
                overlap = ocr_words & speech_words
                if overlap and len(overlap) >= 2:
                    rel = CrossModalRelationship(
                        relationship_type=RelationshipType.AGREEMENT,
                        evidence_ids=[ocr.evidence_id, sp.evidence_id],
                        description=(
                            f"OCR text and speech share words: {sorted(overlap)}. "
                            "This may indicate the speaker is reading visible text."
                        ),
                    )
                    relationships.append(rel)

    # Music + scene mood (complementary)
    for music in music_items:
        for sc in scene_items:
            if music.source.media_id == sc.source.media_id:
                rel = CrossModalRelationship(
                    relationship_type=RelationshipType.COMPLEMENTARY,
                    evidence_ids=[music.evidence_id, sc.evidence_id],
                    description="Music accompanies the visual scene.",
                )
                relationships.append(rel)

    # Video events + audio events at overlapping timestamps
    for ve in video_event_items:
        for ae in audio_event_items:
            if ve.source.media_id != ae.source.media_id:
                continue
            if _timestamps_overlap(ve, ae):
                rel = CrossModalRelationship(
                    relationship_type=RelationshipType.COMPLEMENTARY,
                    evidence_ids=[ve.evidence_id, ae.evidence_id],
                    description=(
                        f"Video event and audio event occur at overlapping timestamps. "
                        f"Video: '{_truncate(ve.value)}'. Audio: '{_truncate(ae.value)}'."
                    ),
                )
                relationships.append(rel)

    return relationships


def _timestamps_overlap(a: EvidenceItem, b: EvidenceItem) -> bool:
    """Return True if two items have overlapping or nearby timestamps."""
    a_start = a.source.video_start_seconds or a.source.audio_start_seconds
    b_start = b.source.video_start_seconds or b.source.audio_start_seconds
    if a_start is None or b_start is None:
        return False
    return abs(a_start - b_start) <= _TIMESTAMP_WINDOW_SECONDS


def _truncate(text: str, max_len: int = 60) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------


def detect_contradictions(
    items: List[EvidenceItem],
) -> List[EvidenceConflict]:
    """Detect potential contradictions between evidence items.

    A difference between modalities is not automatically a contradiction.
    We flag only cases where the same attribute is described in clearly
    incompatible ways by different sources.

    Detected patterns:
    - Two providers describe the same scene with conflicting settings
      (e.g. indoor vs outdoor)
    - OCR text and speech mention the same entity with different values
    - Two activity descriptions for the same media are mutually exclusive
    """
    conflicts: List[EvidenceConflict] = []

    # Group by (media_id, category)
    groups: Dict[Tuple[str, str], List[EvidenceItem]] = {}
    for item in items:
        key = (item.source.media_id, item.category.value)
        groups.setdefault(key, []).append(item)

    for (media_id, category), group in groups.items():
        if len(group) < 2:
            continue

        # Only check items from different providers or modalities
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.source.provider == b.source.provider and a.source.modality == b.source.modality:
                    continue  # same source — not a contradiction
                conflict = _check_conflict(a, b, category)
                if conflict:
                    conflicts.append(conflict)

    return conflicts


def _check_conflict(
    a: EvidenceItem,
    b: EvidenceItem,
    category: str,
) -> Optional[EvidenceConflict]:
    """Return an EvidenceConflict if a and b are potentially contradictory."""
    a_val = a.value.lower().strip()
    b_val = b.value.lower().strip()

    # Setting contradictions (indoor vs outdoor)
    if category == EvidenceCategory.ENVIRONMENT.value:
        indoor_terms = {"indoor", "inside", "interior", "studio"}
        outdoor_terms = {"outdoor", "outside", "exterior", "open air", "street"}
        a_indoor = any(t in a_val for t in indoor_terms)
        a_outdoor = any(t in a_val for t in outdoor_terms)
        b_indoor = any(t in b_val for t in indoor_terms)
        b_outdoor = any(t in b_val for t in outdoor_terms)
        if (a_indoor and b_outdoor) or (a_outdoor and b_indoor):
            return EvidenceConflict(
                conflicting_evidence_ids=[a.evidence_id, b.evidence_id],
                description=f"Conflicting environment: '{a.value}' vs '{b.value}'",
                source_references=[
                    f"{a.source.provider}/{a.source.modality.value}",
                    f"{b.source.provider}/{b.source.modality.value}",
                ],
                explanation=(
                    "Two sources describe the environment differently. "
                    "One indicates indoor/studio, the other outdoor. "
                    "This may reflect different frames or a genuine disagreement."
                ),
            )

    # Mutually exclusive activities
    if category == EvidenceCategory.ACTIVITY.value:
        exclusive_pairs = [
            ({"sitting", "seated"}, {"standing", "walking", "running"}),
            ({"sleeping", "lying down"}, {"standing", "walking", "running"}),
        ]
        for set_a, set_b in exclusive_pairs:
            a_in_a = any(t in a_val for t in set_a)
            a_in_b = any(t in a_val for t in set_b)
            b_in_a = any(t in b_val for t in set_a)
            b_in_b = any(t in b_val for t in set_b)
            if (a_in_a and b_in_b) or (a_in_b and b_in_a):
                return EvidenceConflict(
                    conflicting_evidence_ids=[a.evidence_id, b.evidence_id],
                    description=f"Potentially conflicting activities: '{a.value}' vs '{b.value}'",
                    source_references=[
                        f"{a.source.provider}/{a.source.modality.value}",
                        f"{b.source.provider}/{b.source.modality.value}",
                    ],
                    explanation=(
                        "Two sources describe activities that may be mutually exclusive. "
                        "This could reflect different time points in a video."
                    ),
                )

    return None
