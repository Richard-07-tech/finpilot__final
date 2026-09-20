from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal


Direction = Literal["credit", "debit"]


@dataclass(frozen=True, slots=True)
class TransactionRecord:
    id: str
    date: date
    merchant: str
    description: str
    amount: Decimal
    direction: Direction
    currency: str
    source_account: str
    category: str | None = None

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError("Transaction amount cannot be negative.")

        if self.direction not in ("credit", "debit"):
            raise ValueError(
                f"Invalid transaction direction: {self.direction}"
            )

        if not self.currency.strip():
            raise ValueError("Transaction currency cannot be empty.")

    @property
    def signed_amount(self) -> Decimal:
        if self.direction == "credit":
            return self.amount
        return -self.amount

    @property
    def is_expense(self) -> bool:
        """Return True when this transaction represents an expense."""
        return self.direction == "debit" and self.category not in {
            "Transfer",
            "Income",
        }


@dataclass(frozen=True, slots=True)
class CategoryResult:
    category: str
    confidence: float
    method: str
    matched_rule: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Category confidence must be between 0.0 and 1.0."
            )


@dataclass(frozen=True, slots=True)
class RecurringPayment:
    merchant: str
    currency: str
    frequency: str
    typical_amount: Decimal
    next_expected_date: date | None
    confidence: float
    transaction_count: int

    def __post_init__(self) -> None:
        if self.typical_amount < Decimal("0"):
            raise ValueError(
                "Typical recurring amount cannot be negative."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Recurring confidence must be between 0.0 and 1.0."
            )

        if self.transaction_count < 2:
            raise ValueError(
                "A recurring payment requires at least two transactions."
            )


@dataclass(frozen=True, slots=True)
class Anomaly:
    source: str
    date: date
    merchant: str
    category: str
    amount: Decimal
    baseline: Decimal
    score: float
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount cannot be negative")

        if self.baseline < 0:
            raise ValueError("baseline cannot be negative")

        if self.score < 0:
            raise ValueError("score cannot be negative")


@dataclass(frozen=True, slots=True)
class CategorySpending:
    category: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    """
    Deterministic monthly financial summary.
    """

    month: str
    currency: str
    income: Decimal
    expenses: Decimal
    savings: Decimal
    savings_rate: float
    category_totals: dict[str, Decimal] = field(default_factory=dict)
    top_categories: tuple[CategorySpending, ...] = ()
    recurring_total: Decimal = Decimal("0")
    anomaly_count: int = 0

    def __post_init__(self) -> None:
        if self.income < Decimal("0"):
            raise ValueError("Income cannot be negative.")

        if self.expenses < Decimal("0"):
            raise ValueError("Expenses cannot be negative.")

        if self.recurring_total < Decimal("0"):
            raise ValueError(
                "Recurring total cannot be negative."
            )

        if self.anomaly_count < 0:
            raise ValueError(
                "Anomaly count cannot be negative."
            )

@dataclass(frozen=True, slots=True)
class BudgetStatus:
    category: str
    budget: Decimal
    spent: Decimal
    remaining: Decimal
    utilization: float
    projected_spend: Decimal
    status: str

    def __post_init__(self) -> None:
        if self.budget < 0:
            raise ValueError("budget cannot be negative")

        if self.spent < 0:
            raise ValueError("spent cannot be negative")

        if self.projected_spend < 0:
            raise ValueError("projected_spend cannot be negative")

        if self.utilization < 0:
            raise ValueError("utilization cannot be negative")

@dataclass(frozen=True, slots=True)
class GoalStatus:
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date
    remaining: Decimal
    current_monthly_savings: Decimal
    required_monthly_savings: Decimal
    projected_months: float | None
    on_track: bool
    monthly_shortfall: Decimal

    def __post_init__(self) -> None:
        if self.target_amount < 0:
            raise ValueError("target_amount cannot be negative")

        if self.current_amount < 0:
            raise ValueError("current_amount cannot be negative")

        if self.remaining < 0:
            raise ValueError("remaining cannot be negative")

        if self.required_monthly_savings < 0:
            raise ValueError("required_monthly_savings cannot be negative")

        if self.monthly_shortfall < 0:
            raise ValueError("monthly_shortfall cannot be negative")