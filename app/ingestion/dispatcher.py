"""Route uploaded files to the appropriate ingestion parser."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.parsers import csv_parser, ocr_parser, pdf_parser
from app.ingestion.parsers.csv_parser import RawTransaction


class UnsupportedFileError(Exception):
    """Raised when an upload's detected type has no supported parser."""


def dispatch(file_path: Path, sniffed_content_type: str) -> list[RawTransaction]:
    """Parse ``file_path`` using the parser selected by content sniffing or file extension."""
    suffix = Path(file_path).suffix.lower()
    if sniffed_content_type == "application/pdf" or suffix == ".pdf":
        return pdf_parser.parse(file_path)
    if sniffed_content_type in {"image/jpeg", "image/png"} or suffix in {".jpg", ".jpeg", ".png"}:
        return ocr_parser.parse(file_path)
    if suffix in {".csv", ".xlsx", ".xls"}:
        return csv_parser.parse(file_path)
    raise UnsupportedFileError(sniffed_content_type or suffix)
