from datetime import date
from decimal import Decimal
from app.intelligence.categorization.llm import LLMCategoryFallback
from app.intelligence.categorization.service import Categorizer
from app.intelligence.models import TransactionRecord


def make_transaction(
    merchant: str,
    description: str = "",
) -> TransactionRecord:
    return TransactionRecord(
        id="test-1",
        date=date(2026, 9, 19),
        merchant=merchant,
        description=description,
        amount=Decimal("500.00"),
        direction="debit",
        currency="INR",
        source_account="TEST",
    )


def test_swiggy_is_food() -> None:
    categorizer = Categorizer()

    result = categorizer.classify(
        make_transaction("Swiggy"),
        "user-1",
    )

    assert result.category == "Food & Dining"
    assert result.method == "system_rule"
    assert result.confidence == 0.99


def test_netflix_is_subscription() -> None:
    categorizer = Categorizer()

    result = categorizer.classify(
        make_transaction("Netflix"),
        "user-1",
    )

    assert result.category == "Subscriptions"


def test_unknown_merchant_uses_llm_fallback() -> None:
    def fake_classifier(merchant, description):
        return "Other", 0.5, "No matching deterministic rule"

    categorizer = Categorizer(
        llm_fallback=LLMCategoryFallback(fake_classifier)
    )

    result = categorizer.classify(
        make_transaction("Some Unknown Merchant"),
        "user-1",
    )

    assert result.category == "Other"
    assert result.method == "llm"
    assert result.confidence == 0.5


def test_user_rule_overrides_system_rule() -> None:
    categorizer = Categorizer()

    categorizer.add_user_rule(
        user_id="user-1",
        merchant="Swiggy",
        category="Groceries",
    )

    result = categorizer.classify(
        make_transaction("Swiggy"),
        "user-1",
    )

    assert result.category == "Groceries"
    assert result.method == "user_rule"