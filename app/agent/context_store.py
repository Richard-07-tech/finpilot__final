import json
import sqlite3
import uuid
from pathlib import Path

from .contracts import ChatTurn, SessionContext


class ContextStore:
    """SQLite persistence for chat sessions and cached user budget goals."""

    def __init__(self, db_path: str | Path = "context.db") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    turns TEXT NOT NULL DEFAULT '[]',
                    budget_goals TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    budget_goals TEXT
                )
                """
            )

    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        with self._connect() as connection:
            preference = connection.execute(
                "SELECT budget_goals FROM user_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            budget_goals = preference["budget_goals"] if preference else None
            connection.execute(
                """
                INSERT INTO sessions (session_id, user_id, turns, budget_goals)
                VALUES (?, ?, '[]', ?)
                """,
                (session_id, user_id, budget_goals),
            )
        return session_id

    def append_turn(self, session_id: str, turn: ChatTurn) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT turns FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown session: {session_id}")

            turns = json.loads(row["turns"])
            turns.append(turn.model_dump(mode="json"))
            connection.execute(
                "UPDATE sessions SET turns = ? WHERE session_id = ?",
                (json.dumps(turns), session_id),
            )

    def get_session(self, session_id: str) -> SessionContext | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, user_id, turns, budget_goals
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._context_from_row(row)

    def get_recent_turns(self, session_id: str, n: int) -> list[ChatTurn]:
        session = self.get_session(session_id)
        if session is None:
            return []
        if n <= 0:
            return []
        return session.turns[-n:]

    def set_budget_goals(self, user_id: str, budget_goals: dict) -> None:
        encoded_goals = json.dumps(budget_goals)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_preferences (user_id, budget_goals)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET budget_goals = excluded.budget_goals
                """,
                (user_id, encoded_goals),
            )
            connection.execute(
                "UPDATE sessions SET budget_goals = ? WHERE user_id = ?",
                (encoded_goals, user_id),
            )

    @staticmethod
    def _context_from_row(row: sqlite3.Row) -> SessionContext:
        raw_goals: str | None = row["budget_goals"]
        return SessionContext(
            session_id=row["session_id"],
            user_id=row["user_id"],
            turns=[ChatTurn.model_validate(turn) for turn in json.loads(row["turns"])],
            budget_goals=json.loads(raw_goals) if raw_goals is not None else None,
        )


# The application-facing helpers keep the chat endpoint independent of the
# persistence implementation.  Tests and deployments can replace this store
# by monkeypatching these functions without changing the orchestrator.
_default_store = ContextStore()


def create_session(user_id: str) -> str:
    return _default_store.create_session(user_id)


def append_turn(session_id: str, turn: ChatTurn) -> None:
    _default_store.append_turn(session_id, turn)


def get_session(session_id: str) -> SessionContext | None:
    return _default_store.get_session(session_id)


def get_recent_turns(session_id: str, n: int) -> list[ChatTurn]:
    return _default_store.get_recent_turns(session_id, n)


__all__ = [
    "ContextStore",
    "append_turn",
    "create_session",
    "get_recent_turns",
    "get_session",
]
