from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.db.models import Transaction
from app.intelligence.models import TransactionRecord


def to_record(tx: Transaction) -> TransactionRecord:
    """Convert the ingestion SQLAlchemy model into the intelligence-layer contract."""
    return TransactionRecord(
        id=str(tx.id),
        date=date.fromisoformat(tx.date),
        merchant=tx.merchant,
        description=tx.description,
        amount=Decimal(str(tx.amount)),
        direction=tx.direction,  # type: ignore[arg-type]
        currency=tx.currency.upper(),
        source_account=tx.source_account,
        category=tx.category,
    )
