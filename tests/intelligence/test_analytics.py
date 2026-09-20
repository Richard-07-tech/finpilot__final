from datetime import date
from decimal import Decimal

from app.intelligence.analytics.monthly import compare_months, month_summary
from app.intelligence.budgets.service import budget_status
from app.intelligence.goals.service import goal_status
from app.intelligence.models import TransactionRecord


def t(i, d, amt, direction, cat):
    return TransactionRecord(str(i), d, "M", "M", Decimal(str(amt)), direction, "INR", "a", cat)


def test_month_summary_excludes_transfers_from_expenses():
    txs = [t(1, date(2026,9,1), 100000, "credit", "Income"), t(2, date(2026,9,2), 20000, "debit", "Housing"), t(3, date(2026,9,3), 10000, "debit", "Transfer")]
    s = month_summary(txs, "2026-09", "INR")
    assert s.income == Decimal("100000")
    assert s.expenses == Decimal("20000")
    assert s.savings == Decimal("80000")


def test_budget_projection_and_status():
    txs = [t(i, date(2026,9,i), 1000, "debit", "Food & Dining") for i in range(1,11)]
    b = budget_status(txs, "Food & Dining", Decimal("20000"), "2026-09", "INR", date(2026,9,10))
    assert b.spent == Decimal("10000")
    assert b.projected_spend == Decimal("30000")
    assert b.status == "near_limit"


def test_goal_status():
    g = goal_status("Emergency Fund", Decimal("100000"), Decimal("40000"), date(2027,3,1), Decimal("10000"), date(2026,9,19))
    assert g.remaining == Decimal("60000")
    assert g.required_monthly_savings > Decimal("0")
    assert g.on_track is True
