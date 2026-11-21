"""Abstract provider interfaces for all AI modalities.

All AI calls go through these interfaces.  Swapping providers requires
only a new implementation class — no changes to the pipeline.
"""

from abc import ABC, abstractmethod
from typing import List


class ProviderError(Exception):
    """Raised when an AI provider call fails."""

    def __init__(self, provider: str, message: str, retryable: bool = False):
        self.provider = provider
        self.message = message
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class ProviderConfigError(ProviderError):
    """Raised when a provider is missing required configuration (e.g. API key)."""

    def __init__(self, provider: str, message: str):
        super().__init__(provider, message, retryable=False)


class VisionProvider(ABC):
    """Analyse one or more images and return structured observations."""

    @abstractmethod
    def analyse(self, request) -> List:
        """Accept a VisionRequest; return List[ImageObservation].

        Raises ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and configured."""
        ...


class VideoUnderstandingProvider(ABC):
    """Analyse a video and return structured temporal observations."""

    @abstractmethod
    def analyse(self, request):
        """Accept a VideoRequest; return VideoObservation.

        Raises ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class AudioTranscriptionProvider(ABC):
    """Convert speech to text."""

    @abstractmethod
    def transcribe(self, request):
        """Accept a TranscriptionRequest; return TranscriptionResult.

        Raises ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class AudioUnderstandingProvider(ABC):
    """Describe non-speech audio content."""

    @abstractmethod
    def analyse(self, request):
        """Accept an AudioUnderstandingRequest; return AudioObservation.

        Raises ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class TextGenerationProvider(ABC):
    """Generate grounded text variants from a prepared prompt."""

    @abstractmethod
    def generate(self, prompt: str, timeout_seconds: int = 120) -> str:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...
