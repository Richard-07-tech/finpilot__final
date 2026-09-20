from datetime import date, timedelta
from decimal import Decimal

from app.intelligence.anomalies.detector import detect_transaction_anomalies
from app.intelligence.models import TransactionRecord


def test_large_transaction_is_flagged():
    txs = [TransactionRecord(str(i), date(2026, 9, i + 1), "Restaurant", "Restaurant", Decimal("500"), "debit", "INR", "a", "Food & Dining") for i in range(6)]
    txs.append(TransactionRecord("x", date(2026, 9, 10), "Restaurant", "Restaurant", Decimal("10000"), "debit", "INR", "a", "Food & Dining"))
    result = detect_transaction_anomalies(txs)
    assert result
    assert result[0].amount == Decimal("10000")
