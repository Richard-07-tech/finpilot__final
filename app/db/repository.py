from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Final
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import inspect, or_, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import (
    Base,
    Budget,
    Goal,
    Subscription,
    Transaction,
    Upload,
    UserCategoryRule,
)

class NormalizedTransaction(BaseModel):
    date: str
    description: str
    merchant: str
    amount: float
    direction: str
    currency: str
    source_account: str
    raw_text: str


_DEFAULT_DATABASE_URL: Final[str] = "sqlite+aiosqlite:///./finpilot.db"
DATABASE_URL: Final[str] = os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL)
engine: AsyncEngine = create_async_engine(DATABASE_URL, future=True)
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session for FastAPI dependency injection."""
    async with async_session_factory() as session:
        yield session


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_upload(session: AsyncSession, upload_id: UUID) -> Upload:
    upload = await session.get(Upload, upload_id)
    if upload is None:
        raise ValueError(f"upload {upload_id} does not exist")
    return upload


async def create_upload(filename: str, content_type: str) -> Upload:
    async with async_session_factory() as session:
        upload = Upload(
            filename=filename,
            content_type=content_type,
            status="pending",
        )
        session.add(upload)
        await session.commit()
        await session.refresh(upload)
        return upload


async def mark_upload_completed(upload_id: UUID, row_count: int) -> None:
    async with async_session_factory() as session:
        upload = await _get_upload(session, upload_id)
        upload.status = "completed"
        upload.row_count = row_count
        upload.error_message = None
        upload.completed_at = _utc_now()
        await session.commit()


async def mark_upload_failed(upload_id: UUID, error_message: str) -> None:
    async with async_session_factory() as session:
        upload = await _get_upload(session, upload_id)
        upload.status = "failed"
        upload.error_message = error_message
        upload.completed_at = _utc_now()
        await session.commit()


async def save_transactions(
    upload_id: UUID,
    transactions: list[NormalizedTransaction],
    user_id: str | None = None,
) -> int:
    async with async_session_factory() as session:
        await _get_upload(session, upload_id)
        records = [
            Transaction(
                upload_id=upload_id,
                user_id=user_id,
                date=transaction.date,
                description=transaction.description,
                merchant=transaction.merchant,
                amount=transaction.amount,
                direction=transaction.direction,
                currency=transaction.currency,
                source_account=transaction.source_account,
                raw_text=transaction.raw_text,
            )
            for transaction in transactions
        ]
        if records:
            session.add_all(records)
            await session.commit()
        return len(records)


async def get_transactions_by_upload(upload_id: UUID | str) -> list[Transaction]:
    if isinstance(upload_id, str):
        upload_id = UUID(upload_id)
    async with async_session_factory() as session:
        result = await session.scalars(
            select(Transaction)
            .where(Transaction.upload_id == upload_id)
            .order_by(Transaction.date, Transaction.created_at)
        )
        return list(result.all())


async def get_transactions_by_date_range(start: str, end: str) -> list[Transaction]:
    async with async_session_factory() as session:
        result = await session.scalars(
            select(Transaction)
            .where(Transaction.date >= start, Transaction.date <= end)
            .order_by(Transaction.date, Transaction.created_at)
        )
        return list(result.all())


async def get_existing_signatures() -> set[tuple[str, float, str, str]]:
    """Return all unique (date, amount, merchant, source_account) signatures in the database."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Transaction.date, Transaction.amount, Transaction.merchant, Transaction.source_account)
        )
        return {tuple(row) for row in result.all()}

async def get_transactions_for_upload(upload_id: UUID) -> list[Transaction]:
    """Return all transactions belonging to one upload."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Transaction)
            .where(Transaction.upload_id == upload_id)
            .order_by(Transaction.date.asc())
        )
        return list(result.scalars().all())

async def update_transaction_categories(updates: dict[UUID, str]) -> int:
    """Persist intelligence-layer category assignments in one transaction."""
    if not updates:
        return 0
    async with async_session_factory() as session:
        count = 0
        for transaction_id, category in updates.items():
            tx = await session.get(Transaction, transaction_id)
            if tx is not None:
                tx.category = category
                count += 1
        await session.commit()
        return count


def _merchant_key(merchant: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", merchant.lower())).strip()


async def set_user_category_rule(user_id: str, merchant: str, category: str) -> None:
    """Upsert a user's merchant-category correction."""
    from datetime import datetime, timezone
    key = _merchant_key(merchant)
    async with async_session_factory() as session:
        result = await session.scalars(
            select(UserCategoryRule).where(UserCategoryRule.user_id == user_id, UserCategoryRule.merchant_key == key)
        )
        rule = result.first()
        now = datetime.now(timezone.utc)
        if rule is None:
            session.add(UserCategoryRule(user_id=user_id, merchant_key=key, category=category, created_at=now, updated_at=now))
        else:
            rule.category = category
            rule.updated_at = now
        await session.commit()


async def get_user_category_rules(user_id: str) -> dict[str, str]:
    async with async_session_factory() as session:
        result = await session.scalars(select(UserCategoryRule).where(UserCategoryRule.user_id == user_id))
        return {rule.merchant_key: rule.category for rule in result.all()}

async def get_transactions_for_user(
    user_id: str | None = None,
    month: str | None = None,
    category: str | None = None,
) -> list[Transaction]:
    async with async_session_factory() as session:
        stmt = select(Transaction)
        if user_id and user_id not in ("undefined", "null", "all"):
            stmt = stmt.where(
                or_(
                    Transaction.user_id == user_id,
                    Transaction.source_account == user_id,
                )
            )

        if month:
            stmt = stmt.where(Transaction.date.startswith(month))

        if category is not None:
            stmt = stmt.where(Transaction.category == category)

        stmt = stmt.order_by(
            Transaction.date.desc(),
            Transaction.created_at.desc(),
        )

        result = await session.scalars(stmt)
        return list(result.all())


async def get_budgets_for_user(user_id: str) -> list[Budget]:
    async with async_session_factory() as session:
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.created_at.asc())
        )
        result = await session.scalars(stmt)
        return list(result.all())


async def create_budget(
    user_id: str,
    limit_amount: float,
    name: str = "Total Budget",
    category: str | None = None,
    spent_amount: float | None = None,
    month: str | None = None,
) -> Budget:
    async with async_session_factory() as session:
        budget = Budget(
            user_id=user_id,
            name=name,
            category=category,
            limit_amount=limit_amount,
            spent_amount=spent_amount,
            month=month,
        )
        session.add(budget)
        await session.commit()
        await session.refresh(budget)
        return budget


async def get_goal(
    user_id: str,
    goal_id: str,
) -> Goal | None:
    async with async_session_factory() as session:
        stmt = select(Goal).where(
            Goal.user_id == user_id,
            Goal.id == goal_id,
        )
        result = await session.scalars(stmt)
        return result.first()


async def create_goal(
    user_id: str,
    name: str,
    target_amount: float,
    current_amount: float = 0.0,
    goal_id: str | None = None,
    target_date: str | None = None,
    is_on_track: bool | None = None,
) -> Goal:
    async with async_session_factory() as session:
        goal = Goal(
            id=goal_id or str(uuid4()),
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            is_on_track=is_on_track,
        )
        session.add(goal)
        await session.commit()
        await session.refresh(goal)
        return goal


async def get_subscriptions_for_user(
    user_id: str,
) -> list[Subscription]:
    async with async_session_factory() as session:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.asc())
        )
        result = await session.scalars(stmt)
        return list(result.all())


async def create_subscription(
    user_id: str,
    merchant: str,
    amount: float,
    frequency: str = "monthly",
    category: str | None = None,
    status: str = "active",
    started_at: str | None = None,
) -> Subscription:
    async with async_session_factory() as session:
        subscription = Subscription(
            user_id=user_id,
            merchant=merchant,
            amount=amount,
            frequency=frequency,
            category=category,
            status=status,
            started_at=started_at,
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription


async def save_user_transaction(
    user_id: str,
    date: str,
    description: str,
    merchant: str,
    amount: float,
    direction: str = "debit",
    currency: str = "INR",
    category: str | None = None,
    source_account: str | None = None,
    upload_id: UUID | None = None,
) -> Transaction:
    async with async_session_factory() as session:
        if upload_id is None:
            upload = Upload(
                filename="manual_entry.csv",
                content_type="text/csv",
                status="completed",
                row_count=1,
            )
            session.add(upload)
            await session.flush()
            upload_id = upload.id

        transaction = Transaction(
            upload_id=upload_id,
            user_id=user_id,
            date=date,
            description=description,
            merchant=merchant,
            amount=amount,
            direction=direction,
            currency=currency,
            source_account=source_account or user_id,
            raw_text=f"{date} {description} {amount}",
            category=category,
        )

        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        return transaction

async def has_subscriptions_table() -> bool:
    async with engine.begin() as connection:
        return await connection.run_sync(
            lambda conn: inspect(conn).has_table("subscriptions")
        )


async def get_latest_uploads(limit: int = 5) -> list[Upload]:
    async with async_session_factory() as session:
        stmt = select(Upload).order_by(Upload.uploaded_at.desc()).limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())


async def get_goals_for_user(user_id: str) -> list[Goal]:
    async with async_session_factory() as session:
        stmt = (
            select(Goal)
            .where(Goal.user_id == user_id)
            .order_by(Goal.created_at.asc())
        )
        result = await session.scalars(stmt)
        return list(result.all())

