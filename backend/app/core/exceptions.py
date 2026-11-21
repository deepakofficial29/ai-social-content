"""Application-wide custom exceptions with structured error codes."""

from typing import Any, Dict, Optional


class AppError(Exception):
    """Base application error."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    error_code = "UNSUPPORTED_MEDIA_TYPE"


class FileTooLargeError(AppError):
    status_code = 413
    error_code = "FILE_TOO_LARGE"


class CorruptedMediaError(AppError):
    status_code = 422
    error_code = "CORRUPTED_MEDIA"


class EmptyFileError(AppError):
    status_code = 422
    error_code = "EMPTY_FILE"


class MediaNotFoundError(AppError):
    status_code = 404
    error_code = "MEDIA_NOT_FOUND"


class JobNotFoundError(AppError):
    status_code = 404
    error_code = "JOB_NOT_FOUND"


class EvidenceNotFoundError(AppError):
    status_code = 404
    error_code = "EVIDENCE_NOT_FOUND"


class StorageError(AppError):
    status_code = 500
    error_code = "STORAGE_ERROR"


class FFprobeError(AppError):
    status_code = 500
    error_code = "FFPROBE_ERROR"


class DatabaseError(AppError):
    status_code = 500
    error_code = "DATABASE_ERROR"
