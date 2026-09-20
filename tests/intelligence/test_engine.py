from datetime import date
from decimal import Decimal

from app.intelligence.engine import IntelligenceEngine
from app.intelligence.categorization.service import Categorizer
from app.intelligence.models import TransactionRecord


def test_engine_categorizes_transactions():
    txs = [TransactionRecord("1", date(2026,9,1), "Swiggy", "UPI SWIGGY", Decimal("500"), "debit", "INR", "a")]
    out = IntelligenceEngine(Categorizer()).categorize(txs, "user-1")
    assert out[0].category == "Food & Dining"
