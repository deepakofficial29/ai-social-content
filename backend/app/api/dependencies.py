"""FastAPI dependency providers."""

from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.config import Settings, get_settings

# Re-export for use in route files
__all__ = ["get_db", "get_settings"]
