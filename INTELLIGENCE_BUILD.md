# FinPilot Intelligence Layer - Kailash

This is the deterministic, explainable analytics layer that sits after Richard's ingestion/normalization pipeline.

## 0. Contract between Richard and Kailash

Richard's pipeline produces `NormalizedTransaction` rows with:

- `date`
- `description`
- `merchant`
- `amount` (positive absolute value)
- `direction` (`debit` / `credit`)
- `currency`
- `source_account`
- `raw_text`

The intelligence layer converts those rows into `TransactionRecord` objects and adds category intelligence. It does **not** parse files.

## 1. Install dependencies

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows activate with `.venv\\Scripts\\activate`.

## 2. Run intelligence tests first

```bash
python -m pytest -q tests/intelligence
```

Expected result in this version: **10 passed**.

Then run the complete suite:

```bash
python -m pytest -q
```

If the existing database tests fail with `ModuleNotFoundError: aiosqlite`, install from `requirements.txt`. The dependency is required by Richard's existing async SQLite repository.

## 3. What each module does

### `app/intelligence/models.py`
Stable internal contracts. Use `Decimal` for money inside analytics even though Richard's existing SQLAlchemy model stores `Float`.

### `categorization/`
1. User-specific merchant correction.
2. Deterministic merchant/keyword rules.
3. LLM fallback.
4. Safe `Other` fallback if no LLM is configured.

Never let the LLM invent a category. It must choose from `CATEGORIES`.

### `recurring/`
Groups debit transactions by merchant + currency, checks interval regularity and amount drift, and predicts the next expected date. No LLM is used.

### `anomalies/`
Uses Median Absolute Deviation (MAD), which is robust to extreme transactions. It detects both transaction-level and monthly-category anomalies.

### `analytics/monthly.py`
Computes income, expenses, savings, savings rate, category totals, and month-over-month changes. Transfers are excluded from expense totals.

### `budgets/`
Calculates actual spending, utilization, remaining budget, and end-of-month projection.

### `goals/`
Calculates remaining amount, required monthly saving rate, projected months, and monthly shortfall.

### `engine.py`
Thin orchestration facade. Keep it boring. Business logic belongs in the specialized modules.

## 4. Category correction flow

When the user corrects a merchant:

```http
POST /intelligence/category-correction
Content-Type: application/json

{
  "user_id": "demo-user",
  "merchant": "Swiggy",
  "category": "Groceries"
}
```

The correction is persisted in `user_category_rules` and takes precedence over the system rules and LLM.

## 5. Categorize stored transactions

```http
POST /intelligence/categorize?user_id=demo-user
```

This loads the user's saved merchant rules, classifies stored transactions, and persists category labels to `transactions.category`.

## 6. Monthly summary

```http
GET /intelligence/monthly-summary?month=2026-09&currency=INR
```

The API returns money values as strings to avoid JSON floating-point ambiguity.

## 7. Plug in the LLM

Do **not** put a provider SDK inside the categorization algorithm. Inject a callable into `LLMCategoryFallback`.

The callable contract is:

```python
classifier(merchant: str, description: str) -> tuple[str, float, str]
```

It must return:

```text
(category, confidence, explanation)
```

and the category must be one of `CATEGORIES`.

For production/hackathon reliability, enforce structured JSON output at the provider boundary and validate it before returning it to `Categorizer`.

## 8. Important financial correctness rules

- Never sum different currencies without an explicit FX conversion layer.
- Never treat credit-card bill payments as new spending if the underlying card transactions are already present.
- Transfers are not expenses.
- Money calculations use `Decimal` inside the intelligence layer.
- The LLM explains computed facts; it does not perform the authoritative arithmetic.
- User corrections override generic merchant rules.
- Unknown merchants must not silently receive a made-up category.

## 9. Recommended next implementation after this layer

Add an agent tool layer around the engine:

```text
get_monthly_summary
get_category_spending
compare_months
get_recurring_payments
get_anomalies
get_budget_status
get_goal_status
```

The agent should call these tools and then compose the natural-language answer from their structured results.
