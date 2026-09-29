"""Create the MVP database tables if they do not already exist."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import models  # noqa: F401 - registers models with Base.metadata
from backend.app.database import Base, engine


def init_db() -> None:
    """Create missing tables without changing existing tables or data."""

    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    init_db()

