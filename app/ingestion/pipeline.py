"""Background orchestration for a single uploaded file."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from app.db import repository
from app.db.models import Upload
from app.ingestion.dispatcher import UnsupportedFileError, dispatch
from app.ingestion.parsers.csv_parser import ParsingError as CsvParsingError
from app.ingestion.parsers.ocr_parser import ParsingError as OcrParsingError
from app.ingestion.parsers.pdf_parser import ParsingError as PdfParsingError

try:  # These modules are supplied by the normalization/validation workstream.
    from app.ingestion.normalize import NormalizationError, normalize_transaction
except ImportError:  # pragma: no cover - only while that workstream is landing
    NormalizationError = Exception
    normalize_transaction = None

try:  # These modules are supplied by the normalization/validation workstream.
    from app.ingestion.validate import deduplicate_and_validate
except ImportError:  # pragma: no cover - only while that workstream is landing
    deduplicate_and_validate = None


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _serialize_flag(flag: Any) -> dict[str, Any]:
    """Adapt the validator's flagged-row value to the API storage shape."""
    if isinstance(flag, dict):
        transaction = flag.get("transaction", flag)
        reason = flag.get("reason", "validation failed")
    elif isinstance(flag, tuple) and len(flag) == 2:
        transaction, reason = flag
    else:
        transaction = getattr(flag, "transaction", flag)
        reason = getattr(flag, "reason", "validation failed")
    return {"transaction": _as_dict(transaction), "reason": str(reason)}


async def _save_flagged_rows(upload_id: UUID, flagged_rows: list[dict[str, Any]]) -> None:
    async with repository.async_session_factory() as session:
        upload = await session.get(Upload, upload_id)
        if upload is None:
            raise ValueError(f"upload {upload_id} does not exist")
        upload.flagged_rows = flagged_rows
        await session.commit()


async def process_upload(
    upload_id: UUID,
    file_path: Path,
    sniffed_content_type: str,
    user_id: str,
) -> None:
    """Parse, normalize, validate, persist, and record diagnostics for an upload."""
    try:
        raw_transactions = dispatch(file_path, sniffed_content_type)
    except (UnsupportedFileError, CsvParsingError, PdfParsingError, OcrParsingError) as error:
        await repository.mark_upload_failed(upload_id, str(error))
        return

    try:
        if normalize_transaction is None or deduplicate_and_validate is None:
            await repository.mark_upload_failed(upload_id, "normalization and validation pipeline is not available")
            return

        normalized = []
        flagged_rows: list[dict[str, Any]] = []
        for raw_transaction in raw_transactions:
            try:
                normalized.append(normalize_transaction(raw_transaction))
            except NormalizationError as error:
                flagged_rows.append({"transaction": _as_dict(raw_transaction), "reason": str(error)})

        existing_signatures = await repository.get_existing_signatures()
        clean_transactions, validation_flags = deduplicate_and_validate(normalized, existing_signatures=existing_signatures)
        flagged_rows.extend(_serialize_flag(flag) for flag in validation_flags)

        await repository.save_transactions(
            upload_id,
            clean_transactions,
            user_id=user_id,
        )

        # Categorize the transactions using the intelligence layer.
        from app.intelligence.db_adapter import to_record
        from app.intelligence.engine import IntelligenceEngine
        from app.intelligence.categorization.service import Categorizer

        saved_transactions = await repository.get_transactions_for_upload(upload_id)

        engine = IntelligenceEngine(Categorizer())
        records = [to_record(tx) for tx in saved_transactions]
        categorized_records = engine.categorize(records, user_id)

        category_updates = {
            tx.id: record.category
            for tx, record in zip(saved_transactions, categorized_records)
            if record.category is not None
        }

        if category_updates:
            await repository.update_transaction_categories(category_updates)

        await _save_flagged_rows(upload_id, flagged_rows)
        await repository.mark_upload_completed(
            upload_id,
            row_count=len(clean_transactions),
        )
    except Exception as error:
        await repository.mark_upload_failed(upload_id, str(error))