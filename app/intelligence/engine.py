from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.intelligence.analytics.monthly import compare_months, month_summary
from app.intelligence.anomalies.detector import detect_monthly_category_anomalies, detect_transaction_anomalies
from app.intelligence.budgets.service import budget_status
from app.intelligence.categorization.service import Categorizer
from app.intelligence.goals.service import goal_status
from app.intelligence.models import GoalStatus, MonthlySummary, TransactionRecord
from app.intelligence.recurring.detector import detect_recurring

@dataclass(slots=True)
class IntelligenceEngine:
    categorizer: Categorizer

    def categorize(self, transactions: list[TransactionRecord], user_id: str) -> list[TransactionRecord]:
        result: list[TransactionRecord] = []
        for tx in transactions:
            classification = self.categorizer.classify(tx, user_id)
            result.append(TransactionRecord(tx.id, tx.date, tx.merchant, tx.description, tx.amount, tx.direction, tx.currency, tx.source_account, classification.category))
        return result

    def recurring(self, transactions: list[TransactionRecord]):
        return detect_recurring(transactions)

    def anomalies(self, transactions: list[TransactionRecord]):
        return detect_transaction_anomalies(transactions) + detect_monthly_category_anomalies(transactions)

    def monthly(self, transactions: list[TransactionRecord], month: str, currency: str) -> MonthlySummary:
        summary = month_summary(transactions, month, currency)
        recurring = self.recurring(transactions)
        recurring_total = sum((r.typical_amount for r in recurring if r.currency == currency.upper() and r.frequency in {"monthly", "weekly", "biweekly"}), Decimal("0"))
        anomalies = self.anomalies(transactions)
        return MonthlySummary(summary.month, summary.currency, summary.income, summary.expenses, summary.savings, summary.savings_rate, summary.category_totals, summary.top_categories, recurring_total, len(anomalies))

    def compare(self, transactions: list[TransactionRecord], current: str, previous: str, currency: str):
        return compare_months(transactions, current, previous, currency)

    def budget(self, transactions: list[TransactionRecord], category: str, budget: Decimal, month: str, currency: str, as_of):
        return budget_status(transactions, category, budget, month, currency, as_of)

    @staticmethod
    def goal(name: str, target: Decimal, current: Decimal, deadline, monthly_savings: Decimal, as_of=None) -> GoalStatus:
        return goal_status(name, target, current, deadline, monthly_savings, as_of)
