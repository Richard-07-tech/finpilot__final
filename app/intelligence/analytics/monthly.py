from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.intelligence.models import MonthlySummary, TransactionRecord

def month_summary(transactions: list[TransactionRecord], month: str, currency: str) -> MonthlySummary:
    if len(month) != 7 or month[4] != "-":
        raise ValueError("month must be YYYY-MM")
    totals: dict[str, Decimal] = defaultdict(Decimal)
    income = Decimal("0")
    expenses = Decimal("0")
    for tx in transactions:
        if tx.currency.upper() != currency.upper() or tx.date.strftime("%Y-%m") != month:
            continue
        if tx.direction == "credit":
            income += tx.amount
        elif tx.direction == "debit" and (tx.category or "Other") != "Transfer":
            expenses += tx.amount
            totals[tx.category or "Other"] += tx.amount
    savings = income - expenses
    savings_rate = float(savings / income) if income else 0.0
    top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:5]
    return MonthlySummary(month, currency.upper(), income, expenses, savings, savings_rate, dict(totals), top)

def compare_months(transactions: list[TransactionRecord], current: str, previous: str, currency: str) -> list[dict[str, object]]:
    def totals(month: str) -> dict[str, Decimal]:
        out: dict[str, Decimal] = defaultdict(Decimal)
        for tx in transactions:
            if tx.currency.upper() == currency.upper() and tx.direction == "debit" and tx.category != "Transfer" and tx.date.strftime("%Y-%m") == month:
                out[tx.category or "Other"] += tx.amount
        return out
    a, b = totals(current), totals(previous)
    categories = set(a) | set(b)
    return [
        {"category": c, "current": a.get(c, Decimal("0")), "previous": b.get(c, Decimal("0")), "change": a.get(c, Decimal("0")) - b.get(c, Decimal("0"))}
        for c in sorted(categories, key=lambda c: a.get(c, Decimal("0")) - b.get(c, Decimal("0")), reverse=True)
    ]
