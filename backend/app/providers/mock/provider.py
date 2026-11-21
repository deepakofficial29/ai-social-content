"""Mock implementations of all provider interfaces."""

from app.providers.base import (
    AudioTranscriptionProvider,
    AudioUnderstandingProvider,
    TextGenerationProvider,
    VideoUnderstandingProvider,
    VisionProvider,
)
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    DetectedObject,
    ExtractedText,
    ImageObservation,
    TranscriptionResult,
    TranscriptionSegment,
    VideoObservation,
)


class MockVisionProvider(VisionProvider):
    def health_check(self) -> bool:
        return True

    def analyse(self, request):
        observations = []
        for image in request.images:
            observations.append(ImageObservation(
                media_id=image.media_id,
                sequence_index=image.sequence_index,
                detected_objects=[
                    DetectedObject(label="test object", confidence=ConfidenceLevel.HIGH)
                ],
                extracted_text=[
                    ExtractedText(text="TEST", confidence=ConfidenceLevel.HIGH)
                ],
                estimated_setting="indoor",
                scene_description="A test image in an indoor setting",
                activities=["presenting"],
                provider="mock",
                model_version="mock-v1",
            ))
        return observations


class MockVideoProvider(VideoUnderstandingProvider):
    def health_check(self) -> bool:
        return True

    def analyse(self, request):
        return VideoObservation(
            media_id=request.media_id,
            overall_description="A deterministic test video",
            key_events=["A test scene is shown"],
            detected_activities=["presenting"],
            has_audio=request.has_audio,
            audio_description="Test audio is present" if request.has_audio else None,
            frames_analysed=1,
            total_duration_seconds=request.duration_seconds,
            provider="mock",
            model_version="mock-v1",
        )


class MockTranscriptionProvider(AudioTranscriptionProvider):
    def health_check(self) -> bool:
        return True

    def transcribe(self, request):
        return TranscriptionResult(
            media_id=request.media_id,
            full_text="This is a deterministic test transcription",
            segments=[
                TranscriptionSegment(
                    text="This is a deterministic test transcription",
                    start_seconds=0.0,
                    end_seconds=2.0,
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
            detected_language="en",
            provider="mock",
            model_version="mock-v1",
        )


class MockAudioUnderstandingProvider(AudioUnderstandingProvider):
    def health_check(self) -> bool:
        return True

    def analyse(self, request):
        return AudioObservation(
            media_id=request.media_id,
            has_speech=True,
            has_music=False,
            ambient_sounds=["test tone"],
            sound_events=["deterministic test event"],
            general_summary="Deterministic test audio",
            provider="mock",
            model_version="mock-v1",
        )


class MockTextGenerationProvider(TextGenerationProvider):
    def health_check(self) -> bool:
        return True

    def generate(self, prompt: str, timeout_seconds: int = 120) -> str:
        return (
            '{"variants":['
            '{"approach":"direct","caption_text":"A test object is visible in an indoor setting.","hashtags":["test"],"cta":"Explore the details.","evidence_ids":[]},'
            '{"approach":"storytelling","caption_text":"The test scene presents an object indoors.","hashtags":["story"],"cta":"Take a closer look.","evidence_ids":[]},'
            '{"approach":"engagement","caption_text":"What stands out in this test scene?","hashtags":["engagement"],"cta":"Share your thoughts.","evidence_ids":[]}'
            ']}'
        )
