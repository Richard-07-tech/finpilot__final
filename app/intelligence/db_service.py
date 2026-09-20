from __future__ import annotations

from uuid import UUID

from app.db import repository
from app.intelligence.categorization.service import Categorizer, load_persisted_user_rules
from app.intelligence.db_adapter import to_record
from app.intelligence.models import CategoryResult


async def categorize_persisted_transactions(user_id: str, categorizer: Categorizer | None = None) -> int:
    """Categorize all stored transactions and persist category labels.

    Existing user rules are loaded first. LLM calls happen only for unmatched merchants.
    """
    categorizer = categorizer or Categorizer()
    await load_persisted_user_rules(categorizer, user_id)

    txs = await repository.get_transactions_by_date_range("0001-01-01", "9999-12-31")
    updates: dict[UUID, str] = {}
    for tx in txs:
        result: CategoryResult = categorizer.classify(to_record(tx), user_id)
        updates[tx.id] = result.category
    return await repository.update_transaction_categories(updates)
