from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from app.intelligence.models import RecurringPayment, TransactionRecord

_FREQUENCIES: tuple[tuple[str, float, float], ...] = (
    ("weekly", 7.0, 2.0),
    ("biweekly", 14.0, 3.0),
    ("monthly", 30.0, 5.0),
    ("quarterly", 91.0, 10.0),
    ("yearly", 365.0, 20.0),
)

def _frequency(intervals: list[int]) -> tuple[str, float] | None:
    if len(intervals) < 2:
        return None
    med = float(median(intervals))
    best: tuple[str, float, float] | None = None
    best_error = float("inf")
    for name, target, tolerance in _FREQUENCIES:
        error = abs(med - target)
        if error <= tolerance and error < best_error:
            best = (name, target, tolerance)
            best_error = error
    return None if best is None else (best[0], med)

def detect_recurring(transactions: list[TransactionRecord], min_occurrences: int = 3, max_amount_variation: float = 0.12) -> list[RecurringPayment]:
    if min_occurrences < 3:
        raise ValueError("min_occurrences must be >= 3")
    groups: dict[tuple[str, str], list[TransactionRecord]] = defaultdict(list)
    for tx in transactions:
        if tx.is_expense:
            groups[(tx.merchant.casefold().strip(), tx.currency.upper())].append(tx)

    results: list[RecurringPayment] = []
    for (merchant_key, currency), items in groups.items():
        items.sort(key=lambda x: x.date)
        if len(items) < min_occurrences:
            continue
        intervals = [(b.date - a.date).days for a, b in zip(items, items[1:])]
        freq = _frequency(intervals)
        if freq is None:
            continue
        frequency, median_interval = freq
        # A median alone can hide alternating gaps (e.g. 9 days then 46 days).
        # Require most intervals to actually fall inside the frequency tolerance.
        target = next(target for name, target, _tol in _FREQUENCIES if name == frequency)
        tolerance = next(tol for name, _target, tol in _FREQUENCIES if name == frequency)
        interval_fit = sum(1 for interval in intervals if abs(interval - target) <= tolerance) / len(intervals)
        if interval_fit < 0.75:
            continue
        amounts = [x.amount for x in items]
        med_amount = median(amounts)
        if med_amount <= 0:
            continue
        amount_variation = max(float(abs(a - Decimal(str(med_amount))) / Decimal(str(med_amount))) for a in amounts)
        if amount_variation > max_amount_variation:
            continue
        interval_consistency = max(0.0, 1.0 - (sum(abs(i - median_interval) for i in intervals) / max(1, len(intervals)) / max(median_interval, 1.0)))
        amount_consistency = max(0.0, 1.0 - amount_variation)
        count_factor = min(1.0, len(items) / 6.0)
        confidence = round(0.45 * interval_consistency + 0.40 * amount_consistency + 0.15 * count_factor, 3)
        confidence = round(confidence * interval_fit, 3)
        next_date = items[-1].date + timedelta(days=round(median_interval))
        results.append(RecurringPayment(items[-1].merchant, currency, frequency, Decimal(str(med_amount)).quantize(Decimal("0.01")), len(items), median_interval, amount_variation, next_date, confidence))
    return sorted(results, key=lambda r: (r.next_expected_date, r.merchant.casefold()))
