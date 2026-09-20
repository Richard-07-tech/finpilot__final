import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel


class RawTransaction(BaseModel):
    date: str          # ISO format, "YYYY-MM-DD"
    description: str   # raw merchant/description text, unmodified
    amount: float
    currency: str       # e.g. "INR", "USD" — default to "INR" if not detectable
    source_account: str # filename or account label if present in the file, else "unknown"
    raw_text: str        # the original row as a string, for audit/debugging


class ParsingError(Exception):
    """Raised when a file cannot be parsed or mapped to the schema."""
    pass


# Candidate header variants (lowercased and space-normalized)
_DATE_VARIANTS = [
    "date",
    "txn date",
    "txndate",
    "transaction date",
    "value date",
    "valuedate",
    "posting date",
    "booking date",
    "trans date",
]

_DESC_VARIANTS = [
    "description",
    "narration",
    "particulars",
    "details",
    "remarks",
    "merchant",
    "payee",
    "transaction details",
    "memo",
]

_DEBIT_VARIANTS = [
    "debit",
    "withdrawal amt",
    "withdrawal amount",
    "withdrawals",
    "withdrawal",
    "dr",
    "debit amt",
    "debit amount",
]

_CREDIT_VARIANTS = [
    "credit",
    "deposit amt",
    "deposit amount",
    "deposits",
    "deposit",
    "cr",
    "credit amt",
    "credit amount",
]

_AMOUNT_VARIANTS = [
    "amount",
    "txn amount",
    "transaction amount",
    "net amount",
    "total",
]

_CURRENCY_VARIANTS = [
    "currency",
    "curr",
    "ccy",
]

_ACCOUNT_VARIANTS = [
    "account",
    "account number",
    "account no",
    "account name",
    "source account",
    "account #",
]

_TYPE_VARIANTS = [
    "type",
    "txn type",
    "transaction type",
    "dr/cr",
    "cr/dr",
    "entry type",
]


def _normalize_header(col_name: Any) -> str:
    """Normalize column header for matching."""
    s = str(col_name).strip().lower()
    s = re.sub(r"[\s_\-\.]+", " ", s)
    return s.strip()


def _find_column(columns: list[str], variants: list[str]) -> Optional[str]:
    """Find the first matching column name based on exact normalized match or prefix/substring match."""
    col_map = {col: _normalize_header(col) for col in columns}
    # 1. Exact match against candidate variants
    for variant in variants:
        for col, norm in col_map.items():
            if norm == variant:
                return col
    # 2. Match if normalized variant is contained in normalized column name or vice-versa
    for variant in variants:
        for col, norm in col_map.items():
            if norm.startswith(variant) or variant in norm:
                return col
    return None


def _parse_date(val: Any) -> str:
    """Parse date from common formats (DD/MM/YYYY, MM-DD-YYYY, YYYY-MM-DD, etc.) into ISO 'YYYY-MM-DD'."""
    if pd.isna(val) or val is None or str(val).strip() == "":
        raise ValueError("Date value is missing or empty")

    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")

    val_str = str(val).strip()

    # If datetime string contains time component, split off date part for format checking
    val_date_part = re.split(r"[ T]", val_str)[0] if (" " in val_str or "T" in val_str) else val_str

    # Explicit format order ensuring DD/MM/YYYY, MM-DD-YYYY, and YYYY-MM-DD are handled correctly
    formats_to_try = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%b %d, %Y",
        "%Y%m%d",
    ]

    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(val_date_part, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try with time formats if present
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback to dateutil parser
    try:
        import dateutil.parser
        dt = dateutil.parser.parse(val_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    raise ValueError(f"Unable to parse date '{val}' into ISO format (YYYY-MM-DD)")


def _clean_amount_and_currency(val: Any) -> tuple[float, Optional[str]]:
    """Clean and parse an amount value and extract any inline currency."""
    if pd.isna(val) or val is None:
        return 0.0, None

    if isinstance(val, (int, float)):
        if pd.isna(val):
            return 0.0, None
        return float(val), None

    s = str(val).strip()
    if not s or s == "-":
        return 0.0, None

    detected_currency = None
    if "$" in s:
        detected_currency = "USD"
    elif "€" in s:
        detected_currency = "EUR"
    elif "£" in s:
        detected_currency = "GBP"
    elif "₹" in s or "INR" in s.upper() or "RS" in s.upper():
        detected_currency = "INR"
    elif "USD" in s.upper():
        detected_currency = "USD"
    elif "EUR" in s.upper():
        detected_currency = "EUR"
    elif "GBP" in s.upper():
        detected_currency = "GBP"

    is_debit = False
    is_credit = False

    # Check for parenthesized negative: (100.00)
    if s.startswith("(") and s.endswith(")"):
        is_debit = True
        s = s[1:-1].strip()

    s_lower = s.lower()
    if s_lower.endswith("dr") or s_lower.endswith("debit"):
        is_debit = True
    elif s_lower.endswith("cr") or s_lower.endswith("credit"):
        is_credit = True

    # Strip symbols, commas, letters, spaces
    clean_str = re.sub(r"[^\d.\-]", "", s)
    if not clean_str or clean_str == "-":
        return 0.0, detected_currency

    try:
        num = float(clean_str)
    except ValueError:
        raise ValueError(f"Unable to parse numeric amount from '{val}'")

    if is_debit:
        num = -abs(num)
    elif is_credit:
        num = abs(num)

    return num, detected_currency


def parse(file_path: Path) -> list[RawTransaction]:
    """
    Parse a CSV or XLSX file containing financial transactions into a list of RawTransaction objects.

    Args:
        file_path: Path to the .csv or .xlsx file.

    Returns:
        A list of RawTransaction objects matching the FinPilot schema.

    Raises:
        ParsingError: If the file cannot be read, contains no valid data,
                      or required schema columns cannot be mapped.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise ParsingError(f"File not found: '{file_path}'")

    if not file_path.is_file():
        raise ParsingError(f"Specified path is not a file: '{file_path}'")

    suffix = file_path.suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        raise ParsingError(
            f"Unsupported file format '{suffix}'. Supported formats are: .csv, .xlsx, .xls"
        )

    # Read the file with pandas
    try:
        if suffix == ".csv":
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin-1")
        else:
            df = pd.read_excel(file_path)
    except pd.errors.EmptyDataError:
        raise ParsingError(f"File '{file_path.name}' is completely empty.")
    except Exception as e:
        raise ParsingError(f"Failed to read file '{file_path.name}': {e}") from e

    # Drop fully blank rows
    df = df.dropna(how="all")

    if df.empty or len(df.columns) == 0:
        raise ParsingError(f"File '{file_path.name}' contains no transaction data rows.")

    columns = [str(c) for c in df.columns]

    # Map schema columns
    date_col = _find_column(columns, _DATE_VARIANTS)
    desc_col = _find_column(columns, _DESC_VARIANTS)
    debit_col = _find_column(columns, _DEBIT_VARIANTS)
    credit_col = _find_column(columns, _CREDIT_VARIANTS)
    amount_col = _find_column(columns, _AMOUNT_VARIANTS)
    currency_col = _find_column(columns, _CURRENCY_VARIANTS)
    account_col = _find_column(columns, _ACCOUNT_VARIANTS)
    type_col = _find_column(columns, _TYPE_VARIANTS)

    # Validate essential column mappings
    missing_fields = []
    if not date_col:
        missing_fields.append("Date (variants: Date, Txn Date, Value Date, Transaction Date)")
    if not desc_col:
        missing_fields.append("Description (variants: Description, Narration, Particulars, Details)")

    has_debit_credit = (debit_col is not None and credit_col is not None)
    has_amount = (amount_col is not None)
    has_single_debit_or_credit = (debit_col is not None or credit_col is not None)

    if not (has_debit_credit or has_amount or has_single_debit_or_credit):
        missing_fields.append("Amount (variants: Amount, Debit, Credit, Withdrawal Amt, Deposit Amt)")

    if missing_fields:
        raise ParsingError(
            f"Unable to map file '{file_path.name}' to schema. Missing required columns: "
            + "; ".join(missing_fields)
            + f". Found columns: {columns}"
        )

    transactions: list[RawTransaction] = []

    for idx, row in df.iterrows():
        # Raw text representation of the row for audit/debugging
        raw_text = ",".join("" if pd.isna(v) else str(v) for v in row.values)

        # 1. Parse Date
        raw_date_val = row[date_col]
        try:
            parsed_date = _parse_date(raw_date_val)
        except Exception as e:
            raise ParsingError(
                f"Row {idx + 1} in '{file_path.name}': failed to parse date '{raw_date_val}': {e}"
            ) from e

        # 2. Description: raw merchant/description text, unmodified
        raw_desc_val = row[desc_col]
        description = "" if pd.isna(raw_desc_val) else str(raw_desc_val)

        # 3. Amount & Currency
        row_currency: Optional[str] = None
        if currency_col is not None and pd.notna(row[currency_col]):
            c_val = str(row[currency_col]).strip()
            if c_val:
                row_currency = c_val.upper()

        if has_debit_credit:
            # Both Debit and Credit columns exist: debit = negative, credit = positive
            try:
                debit_amt, d_curr = _clean_amount_and_currency(row[debit_col])
                credit_amt, c_curr = _clean_amount_and_currency(row[credit_col])
            except Exception as e:
                raise ParsingError(
                    f"Row {idx + 1} in '{file_path.name}': failed to parse debit/credit: {e}"
                ) from e

            # Credit is positive, Debit is negative
            amount = abs(credit_amt) - abs(debit_amt)
            if not row_currency:
                row_currency = c_curr or d_curr
        elif has_amount:
            raw_amt_val = row[amount_col]
            try:
                amount, a_curr = _clean_amount_and_currency(raw_amt_val)
            except Exception as e:
                raise ParsingError(
                    f"Row {idx + 1} in '{file_path.name}': failed to parse amount '{raw_amt_val}': {e}"
                ) from e

            # Adjust sign based on Type / Dr-Cr column if present
            if type_col is not None and pd.notna(row[type_col]):
                t_val = str(row[type_col]).strip().lower()
                if any(k in t_val for k in ["dr", "debit", "withdrawal"]):
                    amount = -abs(amount)
                elif any(k in t_val for k in ["cr", "credit", "deposit"]):
                    amount = abs(amount)

            if not row_currency:
                row_currency = a_curr
        elif debit_col is not None:
            try:
                debit_amt, d_curr = _clean_amount_and_currency(row[debit_col])
            except Exception as e:
                raise ParsingError(
                    f"Row {idx + 1} in '{file_path.name}': failed to parse debit: {e}"
                ) from e
            amount = -abs(debit_amt)
            if not row_currency:
                row_currency = d_curr
        else:  # credit_col is not None
            try:
                credit_amt, c_curr = _clean_amount_and_currency(row[credit_col])
            except Exception as e:
                raise ParsingError(
                    f"Row {idx + 1} in '{file_path.name}': failed to parse credit: {e}"
                ) from e
            amount = abs(credit_amt)
            if not row_currency:
                row_currency = c_curr

        final_currency = row_currency if row_currency else "INR"

        # 4. Source Account: filename or account label if present in the file, else "unknown"
        source_account = "unknown"
        if account_col is not None and pd.notna(row[account_col]):
            acc_val = str(row[account_col]).strip()
            if acc_val:
                source_account = acc_val
        elif file_path.name:
            source_account = file_path.name

        transactions.append(
            RawTransaction(
                date=parsed_date,
                description=description,
                amount=float(amount),
                currency=final_currency,
                source_account=source_account,
                raw_text=raw_text,
            )
        )

    if not transactions:
        raise ParsingError(f"No valid transactions could be parsed from '{file_path.name}'.")

    return transactions
