"""Tests for multimodal evidence schemas — Phase 2.2."""

import pytest
from pydantic import ValidationError

from app.schemas.evidence import (
    AudioObservation,
    BoundingBox,
    ConfidenceLevel,
    DetectedObject,
    ExtractedText,
    FrameObservation,
    ImageObservation,
    MediaEvidence,
    TranscriptionResult,
    TranscriptionSegment,
    VideoObservation,
)


# ---------------------------------------------------------------------------
# ConfidenceLevel
# ---------------------------------------------------------------------------

def test_confidence_level_values():
    assert ConfidenceLevel.HIGH == "high"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.LOW == "low"


# ---------------------------------------------------------------------------
# DetectedObject
# ---------------------------------------------------------------------------

def test_detected_object_defaults():
    obj = DetectedObject(label="cat")
    assert obj.confidence == ConfidenceLevel.MEDIUM
    assert obj.bounding_box is None


def test_detected_object_with_bbox():
    obj = DetectedObject(
        label="product",
        confidence=ConfidenceLevel.HIGH,
        bounding_box=BoundingBox(x=0.1, y=0.2, width=0.5, height=0.3),
    )
    assert obj.bounding_box.x == 0.1


# ---------------------------------------------------------------------------
# ExtractedText
# ---------------------------------------------------------------------------

def test_extracted_text_defaults():
    t = ExtractedText(text="Hello World")
    assert t.confidence == ConfidenceLevel.MEDIUM
    assert t.language is None


def test_extracted_text_with_language():
    t = ExtractedText(text="नमस्ते", confidence=ConfidenceLevel.HIGH, language="hi")
    assert t.language == "hi"


# ---------------------------------------------------------------------------
# ImageObservation
# ---------------------------------------------------------------------------

def test_image_observation_minimal():
    obs = ImageObservation(media_id="abc123")
    assert obs.sequence_index == 0
    assert obs.detected_objects == []
    assert obs.extracted_text == []
    assert obs.provider == ""


def test_image_observation_full():
    obs = ImageObservation(
        media_id="abc123",
        sequence_index=2,
        detected_objects=[DetectedObject(label="person", confidence=ConfidenceLevel.HIGH)],
        extracted_text=[ExtractedText(text="SALE", confidence=ConfidenceLevel.HIGH)],
        dominant_colours=["#FF0000", "white"],
        estimated_setting="indoor",
        scene_description="A person standing in a store",
        activities=["standing", "shopping"],
        mood_or_tone="cheerful",
        notable_details=["red sale sign"],
        spatial_relationships=["person in front of shelves"],
        confidence=ConfidenceLevel.HIGH,
        provider="gemini",
        model_version="gemini-2.0-flash",
        processing_time_ms=1200,
    )
    assert obs.sequence_index == 2
    assert len(obs.detected_objects) == 1
    assert obs.detected_objects[0].label == "person"
    assert obs.extracted_text[0].text == "SALE"
    assert obs.provider == "gemini"


def test_image_observation_sequence_index_preserved():
    """Sequence index must be preserved exactly — critical for carousels."""
    for i in range(5):
        obs = ImageObservation(media_id=f"img_{i}", sequence_index=i)
        assert obs.sequence_index == i


# ---------------------------------------------------------------------------
# VideoObservation
# ---------------------------------------------------------------------------

def test_video_observation_minimal():
    obs = VideoObservation(media_id="vid001")
    assert obs.frame_observations == []
    assert obs.has_audio is False
    assert obs.frames_analysed == 0


def test_video_observation_with_frames():
    frame_obs = FrameObservation(
        timestamp_seconds=5.0,
        frame_index=1,
        observation=ImageObservation(media_id="vid001", sequence_index=0),
    )
    obs = VideoObservation(
        media_id="vid001",
        frame_observations=[frame_obs],
        overall_description="A product demo video",
        key_events=["product shown at 0s", "close-up at 5s"],
        has_audio=True,
        audio_description="Background music with voiceover",
        frames_analysed=1,
        total_duration_seconds=30.0,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert len(obs.frame_observations) == 1
    assert obs.frame_observations[0].timestamp_seconds == 5.0
    assert obs.has_audio is True


def test_frame_observation_timestamp_preserved():
    """Timestamps must be preserved exactly — critical for evidence provenance."""
    frame = FrameObservation(
        timestamp_seconds=12.345,
        frame_index=3,
        observation=ImageObservation(media_id="v1"),
    )
    assert frame.timestamp_seconds == 12.345
    assert frame.frame_index == 3


# ---------------------------------------------------------------------------
# TranscriptionResult
# ---------------------------------------------------------------------------

def test_transcription_result_minimal():
    result = TranscriptionResult(
        media_id="aud001",
        full_text="Hello world",
        provider="openai-whisper",
        model_version="whisper-1",
    )
    assert result.full_text == "Hello world"
    assert result.segments == []
    assert result.is_code_mixed is False


def test_transcription_segment_timestamps():
    seg = TranscriptionSegment(
        text="Hello",
        start_seconds=0.0,
        end_seconds=1.5,
        confidence=ConfidenceLevel.HIGH,
        language="en",
    )
    assert seg.start_seconds == 0.0
    assert seg.end_seconds == 1.5


def test_transcription_result_with_segments():
    result = TranscriptionResult(
        media_id="aud001",
        full_text="Hello world how are you",
        segments=[
            TranscriptionSegment(text="Hello world", start_seconds=0.0, end_seconds=1.5),
            TranscriptionSegment(text="how are you", start_seconds=1.5, end_seconds=3.0),
        ],
        detected_language="en",
        detected_languages=["en"],
        provider="openai-whisper",
        model_version="whisper-1",
    )
    assert len(result.segments) == 2
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[1].end_seconds == 3.0


def test_transcription_code_mixed():
    result = TranscriptionResult(
        media_id="aud002",
        full_text="Aaj ka din bahut good hai",
        detected_language="hi",
        detected_languages=["hi", "en"],
        is_code_mixed=True,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert result.is_code_mixed is True
    assert "en" in result.detected_languages


# ---------------------------------------------------------------------------
# AudioObservation
# ---------------------------------------------------------------------------

def test_audio_observation_minimal():
    obs = AudioObservation(media_id="aud001")
    assert obs.has_speech is None
    assert obs.has_music is None
    assert obs.ambient_sounds == []


def test_audio_observation_music_only():
    obs = AudioObservation(
        media_id="aud001",
        has_speech=False,
        has_music=True,
        music_genre="pop",
        emotional_tone="upbeat",
        background_noise_level="low",
        general_summary="Upbeat pop music with no speech",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert obs.has_speech is False
    assert obs.has_music is True
    assert obs.music_genre == "pop"


def test_audio_observation_environmental():
    obs = AudioObservation(
        media_id="aud002",
        has_speech=False,
        has_music=False,
        ambient_sounds=["rain", "wind", "birds"],
        sound_events=["thunder at ~5s"],
        background_noise_level="medium",
        general_summary="Outdoor nature sounds",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert "rain" in obs.ambient_sounds
    assert len(obs.sound_events) == 1


# ---------------------------------------------------------------------------
# MediaEvidence
# ---------------------------------------------------------------------------

def test_media_evidence_minimal():
    ev = MediaEvidence(collection_id="col001", collection_type="single")
    assert ev.processing_status == "pending"
    assert ev.image_observations == []
    assert ev.video_observation is None
    assert ev.transcription is None
    assert ev.audio_observation is None
    assert ev.has_visual_evidence is False
    assert ev.has_audio_evidence is False
    assert ev.has_transcription is False


def test_media_evidence_image_collection():
    obs = ImageObservation(
        media_id="img001",
        sequence_index=0,
        scene_description="A red apple on a table",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    ev = MediaEvidence(
        collection_id="col001",
        collection_type="single",
        image_observations=[obs],
        processing_status="complete",
        has_visual_evidence=True,
        overall_confidence=ConfidenceLevel.HIGH,
        providers_used=["gemini"],
    )
    assert len(ev.image_observations) == 1
    assert ev.image_observations[0].media_id == "img001"
    assert ev.has_visual_evidence is True


def test_media_evidence_carousel_order_preserved():
    """Carousel image order must be preserved in MediaEvidence."""
    observations = [
        ImageObservation(media_id=f"img_{i}", sequence_index=i)
        for i in range(5)
    ]
    ev = MediaEvidence(
        collection_id="col001",
        collection_type="carousel",
        image_observations=observations,
        processing_status="complete",
    )
    for i, obs in enumerate(ev.image_observations):
        assert obs.sequence_index == i
        assert obs.media_id == f"img_{i}"


def test_media_evidence_partial_failure():
    """Partial failures are recorded without discarding successful results."""
    obs = ImageObservation(media_id="img001", provider="gemini", model_version="gemini-2.0-flash")
    ev = MediaEvidence(
        collection_id="col001",
        collection_type="single",
        image_observations=[obs],
        processing_status="partial",
        processing_errors=["Audio understanding failed: rate limit"],
        has_visual_evidence=True,
    )
    assert ev.processing_status == "partial"
    assert len(ev.processing_errors) == 1
    assert len(ev.image_observations) == 1  # visual evidence preserved


def test_media_evidence_serialisation():
    """MediaEvidence must serialise to JSON without errors."""
    ev = MediaEvidence(
        collection_id="col001",
        collection_type="single",
        image_observations=[
            ImageObservation(
                media_id="img001",
                scene_description="test",
                provider="gemini",
                model_version="gemini-2.0-flash",
            )
        ],
        processing_status="complete",
        has_visual_evidence=True,
    )
    data = ev.model_dump(mode="json")
    assert data["collection_id"] == "col001"
    assert data["image_observations"][0]["media_id"] == "img001"


def test_media_evidence_video_with_audio():
    """Video evidence with transcription and audio observation."""
    ev = MediaEvidence(
        collection_id="col002",
        collection_type="video",
        video_observation=VideoObservation(
            media_id="vid001",
            overall_description="Product demo",
            has_audio=True,
            provider="gemini",
            model_version="gemini-2.0-flash",
        ),
        transcription=TranscriptionResult(
            media_id="vid001",
            full_text="Welcome to our product demo",
            provider="openai-whisper",
            model_version="whisper-1",
        ),
        audio_observation=AudioObservation(
            media_id="vid001",
            has_speech=True,
            general_summary="Voiceover narration",
            provider="gemini",
            model_version="gemini-2.0-flash",
        ),
        processing_status="complete",
        has_visual_evidence=True,
        has_audio_evidence=True,
        has_transcription=True,
        providers_used=["gemini", "openai-whisper"],
    )
    assert ev.video_observation.has_audio is True
    assert ev.transcription.full_text == "Welcome to our product demo"
    assert ev.audio_observation.has_speech is True
    assert "gemini" in ev.providers_used
    assert "openai-whisper" in ev.providers_used
