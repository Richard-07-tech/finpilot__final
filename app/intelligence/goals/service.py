from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from app.intelligence.models import GoalStatus

def goal_status(name: str, target_amount: Decimal, current_amount: Decimal, deadline: date, current_monthly_savings: Decimal, as_of: date | None = None) -> GoalStatus:
    if target_amount < 0 or current_amount < 0:
        raise ValueError("goal amounts cannot be negative")
    as_of = as_of or date.today()
    if deadline <= as_of:
        remaining = max(Decimal("0"), target_amount - current_amount)
        required = remaining
        projected = 0.0 if remaining == 0 else None
        return GoalStatus(name, target_amount, current_amount, deadline, remaining, current_monthly_savings, required, projected, remaining == 0, required)
    remaining = max(Decimal("0"), target_amount - current_amount)
    months = max(1, (deadline.year - as_of.year) * 12 + deadline.month - as_of.month + (1 if deadline.day >= as_of.day else 0))
    required = (remaining / Decimal(months)).quantize(Decimal("0.01")) if remaining else Decimal("0")
    projected = float(remaining / current_monthly_savings) if current_monthly_savings > 0 and remaining > 0 else (0.0 if remaining == 0 else None)
    on_track = remaining == 0 or (current_monthly_savings >= required and projected is not None and projected <= months)
    shortfall = max(Decimal("0"), required - current_monthly_savings)
    return GoalStatus(name, target_amount, current_amount, deadline, remaining, current_monthly_savings, required, projected, on_track, shortfall)
