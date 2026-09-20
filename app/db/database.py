from __future__ import annotations

from app.db.models import Base
from app.db.repository import engine


async def init_db() -> None:
    """Create all database tables if they do not already exist."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
