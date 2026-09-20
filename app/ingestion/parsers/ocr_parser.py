"""OCR parser for receipt and bill images.

This module deliberately produces one transaction per image.  It does not infer
accounts, categories, or persist the result anywhere.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel

try:  # Imported here so callers and tests can replace the OCR boundary easily.
    import pytesseract
except ImportError:  # pragma: no cover - depends on deployment dependencies
    pytesseract = None  # type: ignore[assignment]

if pytesseract is not None:
    import os
    import shutil

    _which_tess = shutil.which(pytesseract.pytesseract.tesseract_cmd)
    if not _which_tess or not _which_tess.lower().endswith(".exe"):
        for _candidate in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.exists(_candidate):
                pytesseract.pytesseract.tesseract_cmd = _candidate
                _tess_dir = os.path.dirname(_candidate)
                if _tess_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = _tess_dir + os.pathsep + os.environ.get("PATH", "")
                break


class RawTransaction(BaseModel):
    date: str
    description: str
    amount: float
    currency: str
    source_account: str
    raw_text: str


class ParsingError(Exception):
    """Raised when a receipt image cannot be converted into a transaction."""


_DATE_PATTERNS = (
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s*\d{2,4}\b"),
    re.compile(r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s*\d{2,4}\b"),
)
_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
)
_TOTAL_RE = re.compile(
    r"\b(?:grand\s*total|amount\s*due|net\s*total|total)\b[^\d\n]{0,30}"
    r"(?P<amount>(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*\d[\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(
    r"(?P<token>(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)\s*\d[\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<![\d/.-])(?P<token>\d[\d,]*(?:\.\d{1,2})?)(?![\d/.-])")
_CURRENCY_MARKERS = (("₹", "INR"), ("RS", "INR"), ("INR", "INR"), ("$", "USD"), ("USD", "USD"), ("€", "EUR"), ("EUR", "EUR"), ("£", "GBP"), ("GBP", "GBP"))
_NON_MERCHANT = re.compile(r"(?:tax invoice|invoice|receipt|bill|date|gstin|phone|tel|www\.|https?://)", re.I)


def _preprocess(file_path: Path):
    """Return a high-contrast image, deskewing it when OpenCV is available."""
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - dependency configuration
        raise ParsingError("Pillow is required to preprocess receipt images") from exc

    try:
        with Image.open(file_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("L")
    except (OSError, ValueError) as exc:
        raise ParsingError(f"could not read image '{file_path}': {exc}") from exc

    # A simple binary image works well for printed receipts and is also a safe
    # fallback when OpenCV is not installed.
    image = image.point(lambda pixel: 0 if pixel < 180 else 255, mode="1")

    try:
        import cv2
        import numpy as np

        pixels = np.array(image.convert("L"))
        coordinates = np.column_stack(np.where(pixels < 128))
        if coordinates.size:
            angle = cv2.minAreaRect(coordinates[:, ::-1])[ -1]
            angle = -(90 + angle) if angle < -45 else -angle
            if 0.25 < abs(angle) < 15:
                height, width = pixels.shape
                matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
                pixels = cv2.warpAffine(
                    pixels, matrix, (width, height), flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=255,
                )
                return Image.fromarray(pixels)
    except ImportError:
        pass
    return image


def _ocr(file_path: Path) -> str:
    if pytesseract is None:  # pragma: no cover - dependency configuration
        raise ParsingError("pytesseract is required to parse receipt images")

    image = _preprocess(file_path)
    try:
        return pytesseract.image_to_string(image, config="--psm 6")
    except (OSError, RuntimeError, pytesseract.TesseractError) as exc:
        raise ParsingError(f"OCR failed for '{file_path.name}': {exc}") from exc


def _parse_date(raw_text: str) -> str:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(raw_text)
        if not match:
            continue
        value = re.sub(r"\s+", " ", match.group(0).strip())
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return date.today().isoformat()


def _currency_for(value: str, raw_text: str) -> str:
    upper_value = value.upper()
    upper_text = raw_text.upper()
    for marker, code in _CURRENCY_MARKERS:
        if marker in upper_value:
            return code
    for marker, code in _CURRENCY_MARKERS:
        if marker in upper_text:
            return code
    return "INR"


def _amount_from_token(token: str) -> float | None:
    number = re.sub(r"[^0-9.]", "", token)
    try:
        return float(number) if number else None
    except ValueError:
        return None


def _extract_amount(raw_text: str) -> tuple[float, str] | None:
    # Prefer explicit total labels.  Last match wins because receipts sometimes
    # include both subtotal and grand total.
    labelled = list(_TOTAL_RE.finditer(raw_text))
    if labelled:
        match = labelled[-1]
        amount = _amount_from_token(match.group("amount"))
        if amount is not None:
            return amount, _currency_for(match.group("amount"), raw_text)

    # Low-confidence fallback: choose the largest explicitly currency-formatted
    # amount.  If there is no currency notation, numeric values still provide a
    # useful final fallback, excluding values that form part of dates.
    candidates = [( _amount_from_token(m.group("token")), m.group("token")) for m in _MONEY_RE.finditer(raw_text)]
    candidates = [(amount, token) for amount, token in candidates if amount is not None]
    if not candidates:
        candidates = [( _amount_from_token(m.group("token")), m.group("token")) for m in _NUMBER_RE.finditer(raw_text)]
        candidates = [(amount, token) for amount, token in candidates if amount is not None]
    if candidates:
        amount, token = max(candidates, key=lambda item: item[0])
        return amount, _currency_for(token, raw_text)
    return None


def _merchant_name(raw_text: str) -> str:
    """Use the first plausible text line, as merchant names normally lead receipts."""
    for line in raw_text.splitlines():
        candidate = re.sub(r"\s+", " ", line).strip(" -:|\t")
        if not candidate or _NON_MERCHANT.search(candidate) or re.search(r"\d", candidate):
            continue
        if len(re.sub(r"[^A-Za-z]", "", candidate)) >= 2:
            return candidate
    return "Unknown merchant"


def parse(file_path: Path) -> list[RawTransaction]:
    """OCR one receipt or bill image into its single raw transaction."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise ParsingError(f"image file not found: '{path}'")

    raw_text = _ocr(path)
    if not raw_text or not raw_text.strip():
        raise ParsingError("OCR produced no readable text")

    extracted = _extract_amount(raw_text)
    if extracted is None:
        raise ParsingError("could not extract a total amount from OCR text")
    amount, currency = extracted

    return [
        RawTransaction(
            date=_parse_date(raw_text),
            description=_merchant_name(raw_text),
            amount=amount,
            currency=currency,
            source_account="unknown",
            raw_text=raw_text,
        )
    ]
