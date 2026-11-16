"""Shared test fixtures and configuration."""

import io
import os
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Set env vars before any app module is imported so lru_cache picks them up.
os.environ["DATABASE_URL"] = "sqlite:///./test_caption.db"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp()
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "false"  # suppress SQLAlchemy echo noise in tests

from app.database.connection import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# Isolated test database
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_caption.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(test_engine, "connect")
def _set_wal(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")


TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    from app.database import models  # noqa – register models with Base
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    from app.database.connection import engine as app_engine
    app_engine.dispose()
    try:
        Path("test_caption.db").unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows may still hold the handle; cleaned up on next run


@pytest.fixture
def client(tmp_path) -> Generator:
    """HTTP test client with isolated storage directory and test DB."""
    # Override STORAGE_DIR so LocalStorage uses tmp_path for this test.
    os.environ["STORAGE_DIR"] = str(tmp_path)
    # Invalidate the lru_cache so the new STORAGE_DIR is picked up.
    from app.core.config import get_settings
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    # Restore original temp dir and clear cache again for next test.
    os.environ["STORAGE_DIR"] = tempfile.mkdtemp()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# FFprobe availability marker
# ---------------------------------------------------------------------------

def ffprobe_available() -> bool:
    """Return True if the configured ffprobe binary is executable.

    Reads FFPROBE_PATH from Settings (which honours the .env file) so that
    a binary not on the system PATH but configured via .env is detected.
    """
    import subprocess
    from app.core.config import get_settings
    try:
        path = get_settings().FFPROBE_PATH
        r = subprocess.run([path, "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def ffmpeg_available() -> bool:
    """Return True if the configured ffmpeg binary is executable."""
    import subprocess
    from app.core.config import get_settings
    try:
        path = get_settings().FFMPEG_PATH
        r = subprocess.run([path, "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, OSError):
        return False


requires_ffprobe = pytest.mark.skipif(
    not ffprobe_available(),
    reason="ffprobe not installed – skipping real media inspection tests. "
           "Install FFmpeg to run these tests.",
)


# ---------------------------------------------------------------------------
# Media file factories
# ---------------------------------------------------------------------------

def make_png(width: int = 10, height: int = 10) -> bytes:
    """Generate a minimal valid PNG in pure Python (no FFmpeg needed)."""
    def chunk(name: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    raw_rows = b""
    for _ in range(height):
        raw_rows += b"\x00" + b"\xff\x00\x00" * width
    idat = chunk(b"IDAT", zlib.compress(raw_rows))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def make_jpeg() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def make_webp() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(0, 255, 0)).save(buf, format="WEBP")
    return buf.getvalue()


def _ffmpeg() -> str:
    """Return the configured ffmpeg executable path."""
    from app.core.config import get_settings
    return get_settings().FFMPEG_PATH


def make_mp4_with_audio(tmp_path: Path) -> Path:
    """Generate a real 1-second MP4 with audio using FFmpeg."""
    import subprocess
    out = tmp_path / "with_audio.mp4"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", str(out),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return out


def make_mp4_silent(tmp_path: Path) -> Path:
    """Generate a real 1-second silent MP4 using FFmpeg."""
    import subprocess
    out = tmp_path / "silent.mp4"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
            "-c:v", "libx264", "-an",
            str(out),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return out


def make_wav(tmp_path: Path) -> Path:
    """Generate a real 1-second WAV file using FFmpeg."""
    import subprocess
    out = tmp_path / "tone.wav"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            str(out),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return out


def make_mp3(tmp_path: Path) -> Path:
    """Generate a real 1-second MP3 file using FFmpeg."""
    import subprocess
    out = tmp_path / "tone.mp3"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:a", "libmp3lame",
            str(out),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return out
