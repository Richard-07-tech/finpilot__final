from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.ingestion.normalize import NormalizedTransaction


def _is_valid_iso_date(date_str: Any) -> bool:
    """Check if date is a non-empty string in strict valid ISO 'YYYY-MM-DD' format."""
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        # Ensure format matches exactly (e.g. 4-digit year, 2-digit month, 2-digit day)
        return dt.strftime("%Y-%m-%d") == date_str.strip()
    except (ValueError, TypeError):
        return False


def deduplicate_and_validate(
    transactions: list[NormalizedTransaction],
    existing_signatures: set[tuple] | None = None,
) -> tuple[list[NormalizedTransaction], list[dict[str, Any]]]:
    """
    Validate and deduplicate a batch of normalized transactions.

    Args:
        transactions: List of NormalizedTransaction objects.
        existing_signatures: Optional set of (date, amount, merchant, source_account)
            tuples representing transactions already persisted in the database.

    Returns:
        tuple: (clean_transactions, flagged_rows)
            - clean_transactions: valid, unique NormalizedTransaction instances.
            - flagged_rows: list of dicts {"transaction": dict, "reason": str}.

    Raises:
        ValueError: If `transactions` is not a list.
    """
    if not isinstance(transactions, list):
        raise ValueError(f"Expected a list of NormalizedTransaction, got {type(transactions).__name__}")

    clean_transactions: list[NormalizedTransaction] = []
    flagged_rows: list[dict[str, Any]] = []
    seen_batch_signatures: set[tuple] = set()

    for tx in transactions:
        tx_dict = tx.model_dump() if hasattr(tx, "model_dump") else tx.dict()  # type: ignore[attr-defined]

        # 1. Check Date: missing or invalid
        if not _is_valid_iso_date(tx.date):
            flagged_rows.append({"transaction": tx_dict, "reason": "Missing or invalid date"})
            continue

        # 2. Check Amount: must be > 0
        if tx.amount is None or math.isnan(tx.amount) or tx.amount <= 0:
            flagged_rows.append({"transaction": tx_dict, "reason": "Amount must be greater than zero"})
            continue

        # 3. Check Merchant: cannot be empty
        if not tx.merchant or not tx.merchant.strip():
            flagged_rows.append({"transaction": tx_dict, "reason": "Merchant name is empty"})
            continue

        # 4. Check Duplication: signature = (date, amount, merchant, source_account)
        signature = (tx.date, tx.amount, tx.merchant, tx.source_account)

        if signature in seen_batch_signatures:
            flagged_rows.append({"transaction": tx_dict, "reason": "Duplicate transaction in current batch"})
            continue

        if existing_signatures is not None and signature in existing_signatures:
            flagged_rows.append({"transaction": tx_dict, "reason": "Duplicate transaction already in database"})
            continue

        # Validated and non-duplicate
        seen_batch_signatures.add(signature)
        clean_transactions.append(tx)

    return clean_transactions, flagged_rows
