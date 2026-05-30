"""Database engine and session management for the Verti Garden Planner.

The data store is a single SQLite file. Its location is configurable via the
``VERTI_DB_PATH`` environment variable so it can be pointed at a mounted volume
in Docker / cloud deployments while defaulting to ``data/verti.db`` locally.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "verti.db"
DB_PATH = Path(os.environ.get("VERTI_DB_PATH", str(DEFAULT_DB_PATH)))

_engine = None


def get_engine():
    """Return a lazily-created singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: Streamlit (and later FastAPI) serve requests
        # across threads; SQLite needs this to share a connection pool safely.
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if they exist)."""
    import verti.models  # noqa: F401  (registers models on SQLModel.metadata)

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Session:
    """Open a new session. Use as a context manager: ``with get_session() as s``."""
    return Session(get_engine())
