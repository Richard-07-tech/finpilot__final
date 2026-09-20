from __future__ import annotations
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.intelligence.models import RecurringPayment, TransactionRecord


class RecurringDetector:
    """
    Detect recurring payments from transaction history.

    A merchant is considered recurring when:
    - it has at least 2 transactions
    - transactions occur at roughly regular intervals
    - amounts are reasonably consistent
    """

    MIN_TRANSACTIONS = 2
    AMOUNT_TOLERANCE = Decimal("0.10")
    INTERVAL_TOLERANCE_DAYS = 5

    def detect(
        self,
        transactions: list[TransactionRecord],
    ) -> list[RecurringPayment]:

        groups: dict[tuple[str, str], list[TransactionRecord]] = defaultdict(list)

        for tx in transactions:
            if tx.direction != "debit":
                continue

            key = (tx.merchant.strip().lower(), tx.currency.upper())
            groups[key].append(tx)

        recurring: list[RecurringPayment] = []

        for (merchant, currency), txs in groups.items():

            if len(txs) < self.MIN_TRANSACTIONS:
                continue

            txs.sort(key=lambda tx: tx.date)

            intervals = [
                (txs[i].date - txs[i - 1].date).days
                for i in range(1, len(txs))
            ]

            if not intervals:
                continue

            average_interval = sum(intervals) / len(intervals)

            if not self._is_regular(intervals, average_interval):
                continue

            amounts = [tx.amount for tx in txs]

            average_amount = sum(amounts, Decimal("0")) / len(amounts)

            if not self._amounts_are_consistent(amounts, average_amount):
                continue

            frequency = self._frequency_from_interval(average_interval)

            if frequency == "monthly":
                year = txs[-1].date.year
                month = txs[-1].date.month + 1

                if month > 12:
                    year += 1
                    month = 1

                day = min(
                    txs[-1].date.day,
                    monthrange(year, month)[1],
                )

                next_date = date(year, month, day)
            else:
                next_date = txs[-1].date.fromordinal(
                    txs[-1].date.toordinal() + round(average_interval)
                )

            confidence = self._confidence(
                len(txs),
                intervals,
                amounts,
                average_interval,
            )

            recurring.append(
                RecurringPayment(
                    merchant=txs[-1].merchant,
                    currency=currency,
                    frequency=frequency,
                    typical_amount=average_amount,
                    next_expected_date=next_date,
                    confidence=confidence,
                    transaction_count=len(txs),
                )
            )

        return recurring

    def _is_regular(
        self,
        intervals: list[int],
        average_interval: float,
    ) -> bool:

        return all(
            abs(interval - average_interval)
            <= self.INTERVAL_TOLERANCE_DAYS
            for interval in intervals
        )

    def _amounts_are_consistent(
        self,
        amounts: list[Decimal],
        average: Decimal,
    ) -> bool:

        if average == 0:
            return False

        return all(
            abs(amount - average) / average <= self.AMOUNT_TOLERANCE
            for amount in amounts
        )

    def _frequency_from_interval(self, days: float) -> str:

        if 5 <= days <= 9:
            return "weekly"

        if 25 <= days <= 35:
            return "monthly"

        if 80 <= days <= 100:
            return "quarterly"

        if 350 <= days <= 380:
            return "yearly"

        return "periodic"

    def _confidence(
        self,
        count: int,
        intervals: list[int],
        amounts: list[Decimal],
        average_interval: float,
    ) -> float:

        interval_variance = sum(
            abs(interval - average_interval)
            for interval in intervals
        ) / len(intervals)

        amount_average = sum(amounts, Decimal("0")) / len(amounts)

        amount_variance = sum(
            abs(amount - amount_average)
            for amount in amounts
        ) / len(amounts)

        interval_score = max(
            0.0,
            1.0 - interval_variance / 10.0,
        )

        if amount_average == 0:
            amount_score = 0.0
        else:
            amount_score = max(
                0.0,
                1.0 - float(amount_variance / amount_average),
            )

        count_score = min(count / 6.0, 1.0)

        return round(
            0.5 * interval_score
            + 0.3 * amount_score
            + 0.2 * count_score,
            3,
        )