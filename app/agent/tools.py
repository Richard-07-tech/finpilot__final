from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Coroutine

from app.agent.contracts import ToolResult
from app.db import repository


def _run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute an async coroutine synchronously and safely across execution contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


def get_budget_status(user_id: str) -> ToolResult:
    """Retrieve per-budget spent vs limit for the user without category dependency.

    Queries real budget and transaction rows from the database.
    """
    try:
        budgets = _run_async(repository.get_budgets_for_user(user_id))
        if not budgets:
            return ToolResult(
                tool_name="get_budget_status",
                success=False,
                error=f"No budget found for user '{user_id}'",
            )

        transactions = _run_async(repository.get_transactions_for_user(user_id))

        results: list[dict[str, Any]] = []
        for b in budgets:
            limit = float(b.limit_amount)
            if b.spent_amount is not None:
                spent = float(b.spent_amount)
            else:
                relevant = [
                    t
                    for t in transactions
                    if t.direction.lower() == "debit"
                    and (not b.month or t.date.startswith(b.month))
                ]
                spent = round(sum(float(t.amount) for t in relevant), 2)

            remaining = round(limit - spent, 2)
            exceeded = spent > limit
            pct_used = round((spent / limit) * 100.0, 2) if limit > 0 else 0.0

            results.append(
                {
                    "budget_id": str(b.id),
                    "name": b.name,
                    "category": b.category or b.name,
                    "limit": limit,
                    "spent": spent,
                    "remaining": remaining,
                    "exceeded": exceeded,
                    "percentage_used": pct_used,
                }
            )

        return ToolResult(
            tool_name="get_budget_status",
            success=True,
            data=results,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_budget_status",
            success=False,
            error=str(exc),
        )


def get_goal_progress(user_id: str, goal_id: str) -> ToolResult:
    """Retrieve saved vs target and on-track status for a financial goal without category dependency."""
    try:
        goal = _run_async(repository.get_goal(user_id, goal_id))
        if goal is None:
            return ToolResult(
                tool_name="get_goal_progress",
                success=False,
                error=f"Goal '{goal_id}' not found for user '{user_id}'",
            )

        saved = float(goal.current_amount)
        target = float(goal.target_amount)
        remaining = max(0.0, round(target - saved, 2))

        if goal.is_on_track is not None:
            on_track = bool(goal.is_on_track)
        elif saved >= target:
            on_track = True
        elif goal.target_date:
            try:
                target_dt = datetime.strptime(goal.target_date, "%Y-%m-%d").date()
                created_dt = (
                    goal.created_at.date()
                    if hasattr(goal.created_at, "date")
                    else datetime.now(timezone.utc).date()
                )
                today = datetime.now(timezone.utc).date()

                if today >= target_dt:
                    on_track = saved >= target
                else:
                    total_days = max(1, (target_dt - created_dt).days)
                    elapsed_days = max(0, (today - created_dt).days)
                    expected_saved = (elapsed_days / total_days) * target
                    on_track = saved >= expected_saved
            except Exception:
                on_track = saved > 0.0
        else:
            on_track = saved > 0.0

        progress_pct = round((saved / target) * 100.0, 2) if target > 0 else 100.0

        data = {
            "goal_id": goal.id,
            "name": goal.name,
            "saved": saved,
            "target": target,
            "remaining": remaining,
            "on_track": on_track,
            "progress_pct": progress_pct,
            "target_date": goal.target_date,
        }

        return ToolResult(
            tool_name="get_goal_progress",
            success=True,
            data=data,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_goal_progress",
            success=False,
            error=str(exc),
        )


def get_spending_by_category(user_id: str, month: str) -> ToolResult:
    """Calculate per-category spending totals for a specified month.

    Depends on the `category` field on transactions. Rows with missing or null
    category are excluded from category sums and noted in ToolResult.error.
    """
    try:
        month_str = month[:7] if len(month) >= 7 else month
        transactions = _run_async(repository.get_transactions_for_user(user_id, month=month_str))

        debit_transactions = [
            t for t in transactions if t.direction.lower() == "debit"
        ]

        category_totals: dict[str, float] = {}
        missing_category_count = 0

        for t in debit_transactions:
            if not t.category or not str(t.category).strip():
                missing_category_count += 1
            else:
                cat = str(t.category).strip()
                category_totals[cat] = round(
                    category_totals.get(cat, 0.0) + float(t.amount), 2
                )

        error_message = (
            f"{missing_category_count} transaction(s) excluded due to missing or null category."
            if missing_category_count > 0
            else None
        )

        return ToolResult(
            tool_name="get_spending_by_category",
            success=True,
            data=category_totals,
            error=error_message,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_spending_by_category",
            success=False,
            error=str(exc),
        )


def compare_to_last_month(
    user_id: str,
    category: str,
    month: str | None = None,
) -> ToolResult:
    """Compare category spending between this month and the preceding month.

    Returns: {this_month, last_month, delta, pct_change}
    """
    try:
        if month:
            this_month = month[:7]
        else:
            transactions = _run_async(
                repository.get_transactions_for_user(user_id, category=category)
            )
            if transactions:
                this_month = transactions[0].date[:7]
            else:
                this_month = datetime.now(timezone.utc).strftime("%Y-%m")

        year, m = int(this_month[:4]), int(this_month[5:7])
        if m == 1:
            last_year, last_m = year - 1, 12
        else:
            last_year, last_m = year, m - 1
        last_month = f"{last_year:04d}-{last_m:02d}"

        this_txns = _run_async(
            repository.get_transactions_for_user(user_id, month=this_month, category=category)
        )
        last_txns = _run_async(
            repository.get_transactions_for_user(user_id, month=last_month, category=category)
        )

        this_month_spent = round(
            sum(float(t.amount) for t in this_txns if t.direction.lower() == "debit"),
            2,
        )
        last_month_spent = round(
            sum(float(t.amount) for t in last_txns if t.direction.lower() == "debit"),
            2,
        )

        delta = round(this_month_spent - last_month_spent, 2)

        if last_month_spent > 0:
            pct_change = round(((this_month_spent - last_month_spent) / last_month_spent) * 100.0, 2)
        elif last_month_spent == 0.0 and this_month_spent > 0.0:
            pct_change = 100.0
        else:
            pct_change = 0.0

        return ToolResult(
            tool_name="compare_to_last_month",
            success=True,
            data={
                "this_month": this_month_spent,
                "last_month": last_month_spent,
                "delta": delta,
                "pct_change": pct_change,
            },
        )
    except Exception as exc:
        return ToolResult(
            tool_name="compare_to_last_month",
            success=False,
            error=str(exc),
        )


def list_subscriptions(user_id: str) -> ToolResult:
    """Retrieve recurring/subscription transactions detected by step 2.

    If the subscriptions table does not exist in the database, returns success=False
    with a clear error rather than guessing.
    """
    try:
        if not _run_async(repository.has_subscriptions_table()):
            return ToolResult(
                tool_name="list_subscriptions",
                success=False,
                error="Subscription table ('subscriptions') does not exist yet. Teammates' step 2 output table not found.",
            )

        subs = _run_async(repository.get_subscriptions_for_user(user_id))
        data = [
            {
                "subscription_id": str(s.id),
                "merchant": s.merchant,
                "amount": float(s.amount),
                "frequency": s.frequency,
                "category": s.category,
                "status": s.status,
                "started_at": s.started_at,
            }
            for s in subs
        ]
        return ToolResult(
            tool_name="list_subscriptions",
            success=True,
            data=data,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="list_subscriptions",
            success=False,
            error=str(exc),
        )


def get_upload_summary(user_id: str) -> ToolResult:
    """Retrieve details on statement uploads and uploaded transaction counts."""
    try:
        uploads = _run_async(repository.get_latest_uploads(limit=5))
        txs = _run_async(repository.get_transactions_for_user(user_id))
        
        upload_data = []
        for u in uploads:
            upload_data.append({
                "upload_id": str(u.id),
                "filename": u.filename,
                "status": u.status,
                "row_count": u.row_count,
                "created_at": str(u.uploaded_at) if hasattr(u, "uploaded_at") else None,
                "flagged_count": len(u.flagged_rows) if u.flagged_rows else 0,
            })
        
        recent_txs = [
            {
                "date": t.date,
                "merchant": t.merchant,
                "amount": float(t.amount),
                "direction": t.direction,
                "category": t.category,
            }
            for t in txs[:10]
        ]
        
        return ToolResult(
            tool_name="get_upload_summary",
            success=True,
            data={
                "total_transactions_in_system": len(txs),
                "latest_uploads": upload_data,
                "sample_transactions": recent_txs,
            },
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_upload_summary",
            success=False,
            error=str(exc),
        )


def get_recent_transactions(
    user_id: str,
    limit: int = 15,
    month: str | None = None,
    category: str | None = None,
) -> ToolResult:
    """Retrieve recent transactions for the user with optional month/category filters."""
    try:
        txs = _run_async(repository.get_transactions_for_user(user_id, month=month, category=category))
        data = [
            {
                "date": t.date,
                "merchant": t.merchant,
                "description": t.description,
                "amount": float(t.amount),
                "direction": t.direction,
                "category": t.category or "Uncategorized",
                "currency": t.currency,
            }
            for t in txs[:limit]
        ]
        return ToolResult(
            tool_name="get_recent_transactions",
            success=True,
            data=data,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_recent_transactions",
            success=False,
            error=str(exc),
        )


def get_financial_summary(user_id: str, month: str | None = None) -> ToolResult:
    """Calculate user's income, expenses, savings, and savings rate."""
    try:
        txs = _run_async(repository.get_transactions_for_user(user_id))
        if not txs:
            return ToolResult(
                tool_name="get_financial_summary",
                success=True,
                data={
                    "income": 0.0,
                    "expenses": 0.0,
                    "savings": 0.0,
                    "savings_rate_pct": 0.0,
                    "message": "No transactions found for this user.",
                },
            )

        # Filter by month if provided; otherwise use the latest transaction's month
        active_month = month[:7] if month else txs[0].date[:7]
        month_txs = [t for t in txs if t.date.startswith(active_month)]
        if not month_txs:
            month_txs = txs  # Fallback to all transactions if none in specified month

        income = sum(float(t.amount) for t in month_txs if t.direction.lower() == "credit")
        expenses = sum(float(t.amount) for t in month_txs if t.direction.lower() == "debit")
        savings = income - expenses
        savings_rate = round(((savings / income) * 100.0), 2) if income > 0 else 0.0

        category_breakdown: dict[str, float] = {}
        for t in month_txs:
            if t.direction.lower() == "debit" and t.category:
                cat = str(t.category).strip()
                category_breakdown[cat] = round(category_breakdown.get(cat, 0.0) + float(t.amount), 2)

        return ToolResult(
            tool_name="get_financial_summary",
            success=True,
            data={
                "month": active_month,
                "income": round(income, 2),
                "expenses": round(expenses, 2),
                "savings": round(savings, 2),
                "savings_rate_pct": savings_rate,
                "category_breakdown": category_breakdown,
                "total_transactions": len(month_txs),
            },
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_financial_summary",
            success=False,
            error=str(exc),
        )


def list_goals(user_id: str) -> ToolResult:
    """Retrieve all savings goals configured for the user."""
    try:
        goals = _run_async(repository.get_goals_for_user(user_id))
        data = [
            {
                "goal_id": g.id,
                "name": g.name,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "target_date": g.target_date,
                "is_on_track": bool(g.is_on_track) if g.is_on_track is not None else (g.current_amount >= g.target_amount),
            }
            for g in goals
        ]
        return ToolResult(
            tool_name="list_goals",
            success=True,
            data=data,
        )
    except Exception as exc:
        return ToolResult(
            tool_name="list_goals",
            success=False,
            error=str(exc),
        )


def get_financial_plan(user_id: str) -> ToolResult:
    """Retrieve both budgets and savings goals representing the user's financial plan."""
    budgets_res = get_budget_status(user_id)
    goals_res = list_goals(user_id)
    return ToolResult(
        tool_name="get_financial_plan",
        success=True,
        data={
            "budgets": budgets_res.data if budgets_res.success else [],
            "goals": goals_res.data if goals_res.success else [],
        },
    )


__all__ = [
    "get_budget_status",
    "get_goal_progress",
    "get_spending_by_category",
    "compare_to_last_month",
    "list_subscriptions",
    "get_upload_summary",
    "get_recent_transactions",
    "get_financial_summary",
    "list_goals",
    "get_financial_plan",
]
