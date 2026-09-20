from __future__ import annotations

import json
import os
import re
import time
import logging

from dotenv import load_dotenv
from google import genai

from app.agent import context_store
from app.agent.contracts import ChatTurn
from app.agent.tools import (
    compare_to_last_month,
    get_budget_status,
    get_financial_plan,
    get_financial_summary,
    get_goal_progress,
    get_recent_transactions,
    get_spending_by_category,
    get_upload_summary,
    list_goals,
    list_subscriptions,
)

load_dotenv()
logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)


# HTTP / gRPC status codes that indicate a transient overload and are safe to retry
_RETRYABLE_CODES = {429, 503, 502, 504}


def _is_retryable(exc: Exception) -> bool:
    """Return True if *exc* looks like a transient API overload worth retrying."""
    msg = str(exc)
    # google-genai surfaces the HTTP status code in the exception message
    for code in _RETRYABLE_CODES:
        if str(code) in msg:
            return True
    # gRPC status names
    return any(kw in msg.upper() for kw in ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED"))


def _call_model(client: genai.Client, model_name: str, prompt: str, max_retries: int = 3) -> str | None:
    """Call *model_name* with *prompt*, retrying transient errors with exponential back-off.

    Returns the response text, or *None* if all retries are exhausted.
    Raises immediately for non-retryable errors.
    """
    delay = 1.0
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = response.text.strip()
            return text if text else None
        except Exception as exc:
            if _is_retryable(exc):
                if attempt < max_retries - 1:
                    logger.warning(
                        "Gemini model %s transient error (attempt %d/%d): %s. Retrying in %.1fs…",
                        model_name, attempt + 1, max_retries, exc, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.warning("Gemini model %s failed after %d retries: %s.", model_name, max_retries, exc)
                    return None
            else:
                # Non-retryable (e.g. invalid API key, bad request) — propagate immediately
                raise


def _tool_data(user_id: str, message: str) -> dict:
    text = message.lower()
    month_match = re.search(r"\b(20\d{2}-\d{2})\b", text)
    month = month_match.group(1) if month_match else None

    # 1. Statement uploads, uploaded files, or imports
    if any(k in text for k in ("upload", "uploaded", "file", "statement", "imported", "import")):
        return get_upload_summary(user_id).model_dump()

    # 2. Financial plan, goals, budgets
    if "plan" in text:
        return get_financial_plan(user_id).model_dump()

    if "goal" in text:
        return list_goals(user_id).model_dump()

    if "budget" in text:
        return get_budget_status(user_id).model_dump()

    # 3. Subscriptions
    if "subscription" in text or "subscriptions" in text:
        return list_subscriptions(user_id).model_dump()

    # 4. Compare to last month
    if "compare" in text or "last month" in text:
        category = None
        for candidate in [
            "Food & Dining",
            "Groceries",
            "Shopping",
            "Transportation",
            "Entertainment",
            "Subscriptions",
            "Healthcare",
            "Utilities",
            "Travel",
        ]:
            if candidate.lower() in text:
                category = candidate
                break

        if category:
            return compare_to_last_month(user_id, category, month).model_dump()

    # 5. Transactions, history, ledger
    if any(k in text for k in ("transaction", "transactions", "ledger", "charges", "history", "recent")):
        return get_recent_transactions(user_id, month=month).model_dump()

    # 6. Savings, income, overall financial summary
    if any(k in text for k in ("saving", "savings", "saved", "save", "income", "summary", "overview", "net", "balance")):
        return get_financial_summary(user_id, month=month).model_dump()

    # 7. Spending by category / expense queries
    if any(
        k in text
        for k in (
            "spending",
            "spend",
            "spent",
            "expense",
            "expenses",
            "how much did i spend",
            "how much have i spent",
            "groceries",
            "food",
            "dining",
            "shopping",
            "transportation",
        )
    ):
        m = month or __import__("datetime").datetime.now().strftime("%Y-%m")
        return get_spending_by_category(user_id, m).model_dump()

    # 8. General financial questions ("how are my finances?", "help me with my money")
    if any(k in text for k in ("finance", "finances", "money", "situation", "status")):
        return get_financial_summary(user_id, month=month).model_dump()

    return {}


def run_turn(session_id: str, message: str) -> str:
    session = context_store.get_session(session_id)

    if session is None:
        raise KeyError(f"Unknown session: {session_id}")

    tool_result = _tool_data(session.user_id, message)

    context_store.append_turn(
        session_id,
        ChatTurn(role="user", content=message),
    )

    history = context_store.get_recent_turns(session_id, 10)

    history_text = "\n".join(
        f"{turn.role}: {turn.content}"
        for turn in history
    )

    prompt = f"""
You are FinPilot, a personal finance decision-support assistant.

Your job is to explain the user's financial data clearly and accurately.

Rules:
- Use only the supplied tool data when discussing financial figures.
- Never invent transactions, amounts, budgets, goals, or subscriptions.
- Do not provide investment or financial advice.
- If data is missing, say that it is missing.
- Keep answers concise and useful.
- Use INR formatting when amounts are in INR.
- Explain important changes or percentages in plain language.

Conversation:
{history_text}

Latest tool result:
{json.dumps(tool_result, default=str)}

User's latest question:
{message}

Answer the user's question directly.
"""

    configured_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    candidate_models = [configured_model, "gemini-flash-latest", "gemini-3-flash-preview", "gemini-flash-lite-latest"]
    # Preserve order while eliminating duplicates
    models_to_try = list(dict.fromkeys(candidate_models))

    answer = None
    last_error = None

    try:
        genai_client = _get_client()
        for model_name in models_to_try:
            try:
                result = _call_model(genai_client, model_name, prompt)
                if result:
                    answer = result
                    break
            except Exception as exc:
                last_error = exc
                logger.warning("Gemini model %s non-retryable error: %s. Trying next fallback…", model_name, exc)
    except Exception as exc:
        last_error = exc
        logger.error("Failed to initialize Gemini client: %s", exc)

    if not answer:
        logger.error("All Gemini model attempts failed. Last error: %s", last_error)
        data = tool_result.get("data") if isinstance(tool_result, dict) else None

        if tool_result.get("tool_name") == "get_spending_by_category" and isinstance(data, dict):
            total = sum(float(value) for value in data.values())
            answer = f"Your total spending this month is ₹{total:,.2f}."
        else:
            answer = "I couldn't reach the AI service right now, but your financial data is available."

    context_store.append_turn(
        session_id,
        ChatTurn(role="assistant", content=answer),
    )

    return answer
