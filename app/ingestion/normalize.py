import math
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RawTransaction(BaseModel):
    date: str          # possibly messy: "12/09/2026", "2026-09-12", "12 Sep 2026"
    description: str   # possibly messy: "AMAZON*7X2KL9", "POS PURCHASE - SWIGGY BLR"
    amount: float
    currency: str
    source_account: str
    raw_text: str


class NormalizedTransaction(BaseModel):
    date: str            # strict ISO "YYYY-MM-DD"
    description: str     # original raw description, UNCHANGED
    merchant: str          # cleaned merchant name, e.g. "Amazon", "Swiggy"
    amount: float           # always positive
    direction: str          # "debit" or "credit"
    currency: str           # ISO 4217 code, e.g. "INR", "USD"
    source_account: str
    raw_text: str


class NormalizationError(Exception):
    """Raised when raw transaction data cannot be normalized into canonical form."""
    pass


# Extensible dictionary mapping known merchant name tokens/variants to canonical names
KNOWN_MERCHANTS: dict[str, str] = {
    "amazon": "Amazon",
    "amzn": "Amazon",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "uber": "Uber",
    "ola": "Ola",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "flipkart": "Flipkart",
    "starbucks": "Starbucks",
    "apple": "Apple",
    "google": "Google",
    "blinkit": "Blinkit",
    "zepto": "Zepto",
    "instamart": "Instamart",
}

# Mapping of currency symbols and text representations to ISO 4217 codes
CURRENCY_MAP: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "cad": "CAD",
    "aud": "AUD",
    "jpy": "JPY",
    "¥": "JPY",
    "sgd": "SGD",
    "aed": "AED",
}


def normalize_date(raw_date: str) -> str:
    """
    Parse date from common formats and normalize to ISO 'YYYY-MM-DD'.
    Handles DD/MM/YYYY, MM-DD-YYYY, YYYY-MM-DD, '12 Sep 2026', 'Sep 12, 2026', etc.

    Raises:
        NormalizationError: If the date cannot be parsed.
    """
    if not raw_date or not str(raw_date).strip():
        raise NormalizationError("Date cannot be empty")

    val_str = str(raw_date).strip()

    # If datetime string contains a time component, isolate the date part
    if (" " in val_str and ":" in val_str) or ("T" in val_str and ":" in val_str):
        val_date_part = re.split(r"[ T]", val_str)[0]
    else:
        val_date_part = val_str

    # Explicit format order ensuring DD/MM/YYYY, MM-DD-YYYY, YYYY-MM-DD and textual dates
    formats_to_try = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%Y%m%d",
    ]

    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(val_date_part, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try full val_str with textual and timestamp formats
    for fmt in [
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback to dateutil if installed
    try:
        import dateutil.parser
        dt = dateutil.parser.parse(val_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    raise NormalizationError(f"Unparseable date: '{raw_date}'")


def clean_merchant_name(raw_description: str) -> str:
    """
    Clean raw description into a canonical merchant name:
    - Strips transaction codes and reference numbers (e.g. '*7X2KL9', '#12345').
    - Strips transaction prefixes ('POS PURCHASE -', 'UPI/', 'NEFT/', etc.).
    - Collapses known variants via the KNOWN_MERCHANTS mapping.
    """
    if not raw_description or not str(raw_description).strip():
        return ""

    text = str(raw_description).strip()

    # 1. Direct check against known merchants before stripping
    for pattern, canonical in KNOWN_MERCHANTS.items():
        if re.search(rf"\b{re.escape(pattern)}(?:\.in|\.com)?\b", text, re.IGNORECASE) or re.search(
            rf"^{re.escape(pattern)}[\*\.\s_]", text, re.IGNORECASE
        ):
            return canonical

    # 2. Strip common transaction type prefixes
    prefix_pattern = (
        r"^(?:pos\s*purchase\s*[-/:]*|pos\s*[-/:]+|upi\s*[-/:]+|neft\s*[-/:]+|"
        r"imps\s*[-/:]+|ach\s*[-/:]+|rtgs\s*[-/:]+|debit\s*card\s*[-/:]+|"
        r"card\s*purchase\s*[-/:]+)\s*"
    )
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

    # 3. Check known merchants again after stripping prefix
    for pattern, canonical in KNOWN_MERCHANTS.items():
        if re.search(rf"\b{re.escape(pattern)}(?:\.in|\.com)?\b", text, re.IGNORECASE) or re.search(
            rf"^{re.escape(pattern)}[\*\.\s_]", text, re.IGNORECASE
        ):
            return canonical

    # 4. Strip transaction codes, references, order IDs, and trailing alphanumeric codes
    text = re.sub(r"[\*#]\s*[A-Za-z0-9]+.*$", "", text)
    text = re.sub(r"/(?:ref|txn|id)?[0-9a-zA-Z]+.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[-/]\s*[0-9A-Za-z]{5,}.*$", "", text)

    # 5. Clean up delimiters and normalize whitespace
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 6. Apply title case if uniformly cased
    if text.isupper() or text.islower():
        text = text.title()

    return text


def normalize_currency(raw_currency: str) -> str:
    """
    Map currency symbols or raw text to an ISO 4217 currency code.
    Defaults to 'INR' if empty or unrecognized.
    """
    # Baseline currency for FinPilot is INR when unspecified or unrecognized
    if not raw_currency or not str(raw_currency).strip():
        return "INR"

    cleaned = str(raw_currency).strip().lower().rstrip(".")

    if cleaned in CURRENCY_MAP:
        return CURRENCY_MAP[cleaned]

    raw_lower = str(raw_currency).strip().lower()
    if raw_lower in CURRENCY_MAP:
        return CURRENCY_MAP[raw_lower]

    # If it is already a 3-letter alphabetic currency code, format uppercase
    alpha_code = re.sub(r"[^a-zA-Z]", "", cleaned)
    if len(alpha_code) == 3:
        return alpha_code.upper()

    # Default to 'INR' as documented baseline currency
    return "INR"


def normalize_amount(raw_amount: float) -> tuple[float, str]:
    """
    Normalize amount to an absolute positive float and determine direction.

    Returns:
        tuple[float, str]: (abs(raw_amount), "debit" if raw_amount < 0 else "credit")

    Raises:
        NormalizationError: If raw_amount is not a valid numeric value.
    """
    try:
        val = float(raw_amount)
    except (ValueError, TypeError) as exc:
        raise NormalizationError(f"Invalid amount value: '{raw_amount}'") from exc

    if math.isnan(val) or math.isinf(val):
        raise NormalizationError(f"Invalid amount value: '{raw_amount}'")

    direction = "debit" if val < 0 else "credit"
    return abs(val), direction


def normalize_transaction(raw: RawTransaction) -> NormalizedTransaction:
    """
    Compose date, merchant, amount, and currency normalizations for a RawTransaction.

    Raises:
        NormalizationError: If any sub-step fails, re-raised with field context.
    """
    try:
        norm_date = normalize_date(raw.date)
    except NormalizationError as exc:
        raise NormalizationError(f"Failed to normalize date '{raw.date}': {exc}") from exc

    try:
        norm_merchant = clean_merchant_name(raw.description)
    except NormalizationError as exc:
        raise NormalizationError(
            f"Failed to clean merchant from description '{raw.description}': {exc}"
        ) from exc

    try:
        norm_amount, direction = normalize_amount(raw.amount)
    except NormalizationError as exc:
        raise NormalizationError(f"Failed to normalize amount '{raw.amount}': {exc}") from exc

    try:
        norm_currency = normalize_currency(raw.currency)
    except NormalizationError as exc:
        raise NormalizationError(
            f"Failed to normalize currency '{raw.currency}': {exc}"
        ) from exc

    return NormalizedTransaction(
        date=norm_date,
        description=raw.description,  # Original raw description UNCHANGED
        merchant=norm_merchant,
        amount=norm_amount,
        direction=direction,
        currency=norm_currency,
        source_account=raw.source_account,
        raw_text=raw.raw_text,
    )
