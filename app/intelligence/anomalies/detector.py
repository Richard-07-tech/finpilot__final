from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import median

from app.intelligence.models import Anomaly, TransactionRecord

_MAD_SCALE = 1.4826

def _mad(values: list[Decimal], center: Decimal) -> Decimal:
    return median([abs(v - center) for v in values])

def _severity(score: float) -> str:
    if score >= 6:
        return "high"
    if score >= 4:
        return "medium"
    return "low"

def detect_transaction_anomalies(transactions: list[TransactionRecord], min_history: int = 5, threshold: float = 4.5) -> list[Anomaly]:
    groups: dict[tuple[str, str], list[TransactionRecord]] = defaultdict(list)
    for tx in transactions:
        if tx.is_expense:
            groups[(tx.category or "Other", tx.currency.upper())].append(tx)
    anomalies: list[Anomaly] = []
    for (category, _currency), items in groups.items():
        if len(items) < min_history:
            continue
        values = [x.amount for x in items]
        center = median(values)
        mad = _mad(values, center)
        for tx in items:
            if mad == 0:
                score = float(tx.amount / center) if center else 0.0
            else:
                score = float(abs(tx.amount - center) / (Decimal(str(_MAD_SCALE)) * mad))
            if score >= threshold:
                anomalies.append(Anomaly("transaction", tx.date, tx.merchant, category, tx.amount, center, round(score, 2), _severity(score), f"{tx.amount:.2f} is unusually high for {category}; robust baseline is {center:.2f}."))
    return sorted(anomalies, key=lambda a: a.score, reverse=True)

def detect_monthly_category_anomalies(transactions: list[TransactionRecord], min_months: int = 4, threshold: float = 3.5) -> list[Anomaly]:
    monthly: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for tx in transactions:
        if tx.is_expense:
            month = tx.date.strftime("%Y-%m")
            monthly[(tx.category or "Other", tx.currency.upper())][month] += tx.amount
    anomalies: list[Anomaly] = []
    for (category, _currency), months in monthly.items():
        if len(months) < min_months:
            continue
        ordered = sorted(months.items())
        values = [v for _, v in ordered]
        center = median(values[:-1])
        mad = _mad(values[:-1], center)
        current_month, current_value = ordered[-1]
        if mad == 0:
            score = float(current_value / center) if center else 0.0
        else:
            score = float(abs(current_value - center) / (Decimal(str(_MAD_SCALE)) * mad))
        if score >= threshold:
            month_date = date.fromisoformat(current_month + "-01")
            anomalies.append(Anomaly("category_month", month_date, None, category, current_value, center, round(score, 2), _severity(score), f"{category} spending in {current_month} is unusually high versus prior months."))
    return sorted(anomalies, key=lambda a: a.score, reverse=True)
