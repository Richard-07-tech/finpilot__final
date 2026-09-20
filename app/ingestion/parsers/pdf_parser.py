from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


class RawTransaction(BaseModel):
    date: str
    description: str
    amount: float
    currency: str = "INR"
    source_account: str = "unknown"
    raw_text: str


class ParsingError(Exception):
    """Raised when a statement contains no transactions that can be parsed."""


_DATE_PATTERN = r"(?:\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
_DATE_RE = re.compile(rf"(?P<date>{_DATE_PATTERN})")
_AMOUNT_RE = re.compile(
    r"(?P<amount>[₹$€£]?\s*[+-]?\(?\s*\d[\d,]*(?:\.\d{1,2})?\s*\)?\s*(?:CR|DR)?)",
    re.IGNORECASE,
)
_ACCOUNT_RES = (
    re.compile(r"(?:account(?:\s+number|\s*no\.?)?|a/c)\s*[:#-]?\s*([A-Za-z0-9][A-Za-z0-9 */-]{3,})", re.I),
    re.compile(r"\b(?:masked\s+)?account\s*[:#-]?\s*(\*{2,}[\dXx-]+|\d{4,})\b", re.I),
)
_CURRENCY_SYMBOLS = (("₹", "INR"), ("$", "USD"), ("€", "EUR"), ("£", "GBP"))
_SKIP_WORDS = ("opening balance", "closing balance", "total", "page ", "statement period")


def _parse_date(value: str) -> str | None:
    for format_string in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ):
        try:
            return datetime.strptime(value.strip(), format_string).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_amount(match: re.Match[str]) -> tuple[float, str]:
    token = match.group("amount").strip()
    currency = "INR"
    for symbol, code in _CURRENCY_SYMBOLS:
        if symbol in token:
            currency = code
            break
    if re.search(r"\bDR\b", token, re.I):
        sign = -1
    else:
        sign = 1
    number = re.sub(r"[^0-9.]", "", token)
    amount = float(number) * sign
    if token.lstrip().startswith("(") and token.rstrip().endswith(")"):
        amount = -abs(amount)
    return amount, currency


def _currency_for(text: str) -> str:
    upper_text = text.upper()
    for code in ("INR", "USD", "EUR", "GBP"):
        if re.search(rf"\b{code}\b", upper_text):
            return code
    for symbol, code in _CURRENCY_SYMBOLS:
        if symbol in text:
            return code
    return "INR"


def _source_account(text: str) -> str:
    for pattern in _ACCOUNT_RES:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return "unknown"


def _is_candidate(text: str) -> bool:
    lower_text = text.lower()
    if any(word in lower_text for word in _SKIP_WORDS):
        return False
    return _DATE_RE.search(text) is not None and _AMOUNT_RE.search(text) is not None


def _transaction_from_text(text: str, source_account: str) -> RawTransaction | None:
    if not _is_candidate(text):
        return None
    date_match = _DATE_RE.search(text)
    amount_matches = list(_AMOUNT_RE.finditer(text))
    if date_match is None or not amount_matches:
        return None
    parsed_date = _parse_date(date_match.group("date"))
    if parsed_date is None:
        return None
    amount_match = amount_matches[-1]
    description = text[date_match.end() : amount_match.start()].strip()
    if not description:
        return None
    amount, amount_currency = _parse_amount(amount_match)
    return RawTransaction(
        date=parsed_date,
        description=description,
        amount=amount,
        currency=amount_currency if amount_currency != "INR" else _currency_for(text),
        source_account=source_account,
        raw_text=text,
    )


def _transactions_from_table(table: list[list[object]], source_account: str) -> list[RawTransaction]:
    if not table or len(table) < 2:
        return []

    headers = [str(h).strip().lower() if h is not None else "" for h in table[0]]
    date_col = next((i for i, h in enumerate(headers) if "date" in h), None)
    desc_col = next((i for i, h in enumerate(headers) if any(k in h for k in ("narrat", "desc", "particular", "detail", "item"))), None)
    with_col = next((i for i, h in enumerate(headers) if i != desc_col and (any(k in h for k in ("withdraw", "debit")) or re.search(r"\bdr\b", h))), None)
    dep_col = next((i for i, h in enumerate(headers) if i != desc_col and (any(k in h for k in ("deposit", "credit")) or re.search(r"\bcr\b", h))), None)
    single_amt_col = next((i for i, h in enumerate(headers) if "amount" in h and i not in (with_col, dep_col, desc_col)), None)

    active_indices = [idx for idx in (date_col, desc_col, with_col, dep_col, single_amt_col) if idx is not None]
    if date_col is None or desc_col is None or not active_indices:
        return []

    results: list[RawTransaction] = []
    max_idx = max(active_indices)
    for row in table[1:]:
        if not row or len(row) <= max_idx:
            continue
        date_raw = str(row[date_col]).strip() if row[date_col] is not None else ""
        parsed_date = _parse_date(date_raw)
        if not parsed_date:
            continue
        desc = str(row[desc_col]).strip() if row[desc_col] is not None else ""
        if not desc or any(w in desc.lower() for w in _SKIP_WORDS):
            continue

        raw_row_text = " ".join(str(c) for c in row if c is not None).strip()
        currency = _currency_for(raw_row_text)

        w_val = str(row[with_col]).strip() if with_col is not None and row[with_col] is not None else ""
        d_val = str(row[dep_col]).strip() if dep_col is not None and row[dep_col] is not None else ""

        if w_val and re.search(r"\d", w_val):
            num = float(re.sub(r"[^0-9.]", "", w_val))
            results.append(RawTransaction(
                date=parsed_date,
                description=desc,
                amount=-abs(num),  # negative indicates debit
                currency=currency,
                source_account=source_account,
                raw_text=raw_row_text,
            ))
        elif d_val and re.search(r"\d", d_val):
            num = float(re.sub(r"[^0-9.]", "", d_val))
            results.append(RawTransaction(
                date=parsed_date,
                description=desc,
                amount=abs(num),  # positive indicates credit
                currency=currency,
                source_account=source_account,
                raw_text=raw_row_text,
            ))
        elif single_amt_col is not None and row[single_amt_col] is not None:
            amt_str = str(row[single_amt_col]).strip()
            if re.search(r"\d", amt_str):
                num = float(re.sub(r"[^0-9.]", "", amt_str))
                sign = -1 if any(k in desc.lower() for k in ("debit", "dr", "purchase", "rent", "fee", "order")) else 1
                results.append(RawTransaction(
                    date=parsed_date,
                    description=desc,
                    amount=num * sign,
                    currency=currency,
                    source_account=source_account,
                    raw_text=raw_row_text,
                ))
    return results


def _table_rows(page: object) -> Iterable[str]:
    tables = page.extract_tables()  # type: ignore[attr-defined]
    for table in tables or []:
        for row in table or []:
            cells = [cell if cell is not None else "" for cell in row]
            text = " ".join(cells).strip()
            if text:
                yield text


def parse(file_path: Path) -> list[RawTransaction]:
    """Extract statement transactions from all pages of a text-based PDF."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise ParsingError("pdfplumber is required to parse PDF statements") from exc

    table_rows: list[str] = []
    text_lines: list[str] = []
    has_text_layer = False
    all_tables: list[list[list[object]]] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    has_text_layer = True
                    text_lines.extend(line for line in page_text.splitlines() if line.strip())
                page_tables = page.extract_tables() or []
                all_tables.extend(page_tables)
                table_rows.extend(_table_rows(page))
    except OSError as exc:
        raise ParsingError(f"could not read PDF: {exc}") from exc

    source_account = _source_account("\n".join(text_lines + table_rows))

    # Priority 1: Structured table extraction (preserves separate withdrawal/deposit columns)
    transactions: list[RawTransaction] = []
    for table in all_tables:
        t_txs = _transactions_from_table(table, source_account)
        transactions.extend(t_txs)

    if transactions:
        return transactions

    # Priority 2: Text matching across table rows
    for row in table_rows:
        transaction = _transaction_from_text(row, source_account)
        if transaction is not None:
            transactions.append(transaction)

    # Priority 3: Text matching across lines
    if not transactions:
        for line in text_lines:
            transaction = _transaction_from_text(line, source_account)
            if transaction is not None:
                transactions.append(transaction)

    if transactions:
        return transactions
    if not has_text_layer:
        raise ParsingError(
            "no transactions found: this appears to be a scanned/image-only PDF with no text layer; "
            "the OCR pipeline is required"
        )
    raise ParsingError("no transactions found: the PDF has text, but no rows matched the supported date and amount formats")
