import pytest
from datetime import date
from decimal import Decimal

from app.db.database import init_db
from app.db.repository import (
    get_user_category_rules,
    set_user_category_rule,
)
from app.intelligence.categorization.service import (
    Categorizer,
    load_persisted_user_rules,
)
from app.intelligence.models import TransactionRecord


@pytest.mark.asyncio
async def test_persisted_rule_can_be_loaded_into_categorizer() -> None:
    await init_db()
    user_id = "test-persistence-user"

    await set_user_category_rule(
        user_id=user_id,
        merchant="Swiggy",
        category="Groceries",
    )

    rules = await get_user_category_rules(user_id)

    assert rules["swiggy"] == "Groceries"

    categorizer = Categorizer()

    await load_persisted_user_rules(
        categorizer=categorizer,
        user_id=user_id,
    )

    transaction = TransactionRecord(
        id="test-transaction",
        date=date(2026, 9, 19),
        merchant="Swiggy",
        description="UPI/SWIGGY/12345",
        amount=Decimal("450.00"),
        direction="debit",
        currency="INR",
        source_account="TEST",
    )

    result = categorizer.classify(
        transaction=transaction,
        user_id=user_id,
    )

    assert result.category == "Groceries"
    assert result.method == "user_rule"
    assert result.confidence == 1.0