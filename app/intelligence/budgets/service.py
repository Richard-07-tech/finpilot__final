from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from app.intelligence.models import BudgetStatus, TransactionRecord

def budget_status(transactions: list[TransactionRecord], category: str, budget: Decimal, month: str, currency: str, as_of: date | None = None) -> BudgetStatus:
    if budget < 0:
        raise ValueError("budget cannot be negative")
    as_of = as_of or date.today()
    if as_of.strftime("%Y-%m") != month:
        raise ValueError("as_of must belong to the requested month")
    spent = sum((tx.amount for tx in transactions if tx.direction == "debit" and tx.category == category and tx.currency.upper() == currency.upper() and tx.date.strftime("%Y-%m") == month), Decimal("0"))
    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    elapsed = max(1, as_of.day)
    projected = (spent / Decimal(elapsed) * Decimal(days_in_month)).quantize(Decimal("0.01"))
    remaining = budget - spent
    utilization = float(spent / budget) if budget else (1.0 if spent > 0 else 0.0)
    status = "over_budget" if spent > budget else "near_limit" if utilization >= 0.8 or projected > budget else "on_track"
    return BudgetStatus(category, budget, spent, remaining, utilization, projected, status)
