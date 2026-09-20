from datetime import date
from decimal import Decimal

from app.intelligence.models import TransactionRecord
from app.intelligence.recurring.service import RecurringDetector


def make_tx(
    tx_id: str,
    tx_date: date,
    merchant: str,
    amount: str,
) -> TransactionRecord:
    return TransactionRecord(
        id=tx_id,
        date=tx_date,
        merchant=merchant,
        description=f"Payment to {merchant}",
        amount=Decimal(amount),
        direction="debit",
        currency="INR",
        source_account="TEST",
    )


def test_detects_monthly_recurring_payment() -> None:
    transactions = [
        make_tx("1", date(2026, 1, 10), "Netflix", "649"),
        make_tx("2", date(2026, 2, 10), "Netflix", "649"),
        make_tx("3", date(2026, 3, 10), "Netflix", "649"),
    ]

    detector = RecurringDetector()
    results = detector.detect(transactions)

    assert len(results) == 1

    result = results[0]

    assert result.merchant == "Netflix"
    assert result.frequency == "monthly"
    assert result.typical_amount == Decimal("649")
    assert result.transaction_count == 3
    assert result.next_expected_date == date(2026, 4, 10)


def test_ignores_irregular_payments() -> None:
    transactions = [
        make_tx("1", date(2026, 1, 1), "Amazon", "1000"),
        make_tx("2", date(2026, 1, 15), "Amazon", "1000"),
        make_tx("3", date(2026, 3, 20), "Amazon", "1000"),
    ]

    detector = RecurringDetector()
    results = detector.detect(transactions)

    assert results == []


def test_ignores_inconsistent_amounts() -> None:
    transactions = [
        make_tx("1", date(2026, 1, 10), "Netflix", "649"),
        make_tx("2", date(2026, 2, 10), "Netflix", "649"),
        make_tx("3", date(2026, 3, 10), "Netflix", "1299"),
    ]

    detector = RecurringDetector()
    results = detector.detect(transactions)

    assert results == []


def test_ignores_credit_transactions() -> None:
    transactions = [
        TransactionRecord(
            id="1",
            date=date(2026, 1, 10),
            merchant="Salary",
            description="Salary",
            amount=Decimal("50000"),
            direction="credit",
            currency="INR",
            source_account="TEST",
        ),
        TransactionRecord(
            id="2",
            date=date(2026, 2, 10),
            merchant="Salary",
            description="Salary",
            amount=Decimal("50000"),
            direction="credit",
            currency="INR",
            source_account="TEST",
        ),
    ]

    detector = RecurringDetector()
    results = detector.detect(transactions)

    assert results == []