from pathlib import Path

from app.db.models import Base
from app.db.repository import DATABASE_URL, engine


async def init_db() -> None:
    """Create all database tables if they do not already exist."""
    if "sqlite" in DATABASE_URL and ":///" in DATABASE_URL:
        db_path = DATABASE_URL.split(":///")[-1]
        if db_path and not db_path.startswith(":memory:"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

