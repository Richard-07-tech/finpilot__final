from __future__ import annotations

from datetime import date
import calendar
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import repository
from app.intelligence.db_adapter import to_record
from app.intelligence.engine import IntelligenceEngine
from app.intelligence.categorization.service import Categorizer

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

class CategoryCorrection(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    merchant: str = Field(min_length=1, max_length=255)
    category: str

@router.post("/categorize")
async def categorize_all(user_id: str = "demo-user") -> dict[str, int | str]:
    from app.intelligence.db_service import categorize_persisted_transactions
    count = await categorize_persisted_transactions(user_id)
    return {"updated": count, "user_id": user_id}

@router.post("/category-correction")
async def category_correction(payload: CategoryCorrection) -> dict[str, str]:
    from app.intelligence.categorization.rules import CATEGORIES
    if payload.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of: {', '.join(CATEGORIES)}")
    await repository.set_user_category_rule(payload.user_id, payload.merchant, payload.category)
    return {"status": "saved", "merchant": payload.merchant, "category": payload.category}

@router.get("/monthly-summary")
async def monthly_summary(month: str, currency: str = "INR") -> dict[str, object]:
    try:
        date.fromisoformat(month + "-01")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM") from exc
    year, month_num = map(int, month.split("-"))
    last_day = calendar.monthrange(year, month_num)[1]
    txs = await repository.get_transactions_by_date_range(month + "-01", f"{month}-{last_day:02d}")
    engine = IntelligenceEngine(Categorizer())
    records = [to_record(tx) for tx in txs]
    summary = engine.monthly(records, month, currency)
    return {
        "month": summary.month,
        "currency": summary.currency,
        "income": str(summary.income),
        "expenses": str(summary.expenses),
        "savings": str(summary.savings),
        "savings_rate": summary.savings_rate,
        "category_totals": {k: str(v) for k, v in summary.category_totals.items()},
        "top_categories": [{"category": k, "amount": str(v)} for k, v in summary.top_categories],
        "recurring_total": str(summary.recurring_total),
        "anomaly_count": summary.anomaly_count,
    }


@router.get("/transactions")
async def list_transactions(
    user_id: str | None = None,
    month: str | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    txs = await repository.get_transactions_for_user(user_id, month=month, category=category)
    return [
        {
            "id": str(tx.id),
            "date": tx.date,
            "description": tx.description,
            "merchant": tx.merchant,
            "amount": tx.amount,
            "direction": tx.direction,
            "currency": tx.currency,
            "source_account": tx.source_account,
            "category": tx.category,
            "user_id": tx.user_id,
        }
        for tx in txs
    ]
