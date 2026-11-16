"""Shared Pydantic response envelope schemas."""

from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    details: Dict[str, Any] = {}


class APIResponse(BaseModel, Generic[DataT]):
    success: bool
    message: str
    data: Optional[DataT] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, message: str, data: DataT | None = None) -> "APIResponse[DataT]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, code: str, details: Dict[str, Any] | None = None) -> "APIResponse":
        return cls(
            success=False,
            message=message,
            error=ErrorDetail(code=code, details=details or {}),
        )
