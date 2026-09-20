from __future__ import annotations
from app.intelligence.categorization.llm import LLMCategoryFallback
from dataclasses import dataclass
from app.db.repository import get_user_category_rules
from app.intelligence.categorization.rules import (
    CATEGORIES,
    CategoryRule,
    SYSTEM_RULES,
)
from app.intelligence.models import TransactionRecord
from app.intelligence.categorization.llm import LLMCategoryFallback

@dataclass(frozen=True, slots=True)
class CategoryResult:
    category: str
    confidence: float
    method: str
    matched_rule: str | None = None


class Categorizer:
    """
    Deterministic transaction categorizer.

    Classification priority:

        1. User-specific rules
        2. System rules
        3. Unmatched

    The database layer is intentionally injected rather than imported
    directly into the classification logic. This keeps the classifier
    easy to test.
    """

    def __init__(
        self,
        system_rules: tuple[CategoryRule, ...] = SYSTEM_RULES,
        llm_fallback: LLMCategoryFallback | None = None,
    ) -> None:
        self.system_rules = system_rules
        self.llm_fallback = llm_fallback or LLMCategoryFallback()

        # In-memory rules are useful for unit tests and temporary rules.
        # Persistent application rules are loaded separately.
        self.user_rules: dict[str, dict[str, str]] = {}

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.lower().strip().split())

    def load_user_rules(
        self,
        user_id: str,
        rules: dict[str, str],
    ) -> None:
        """
        Load persisted rules into the in-memory classifier.

        The repository stores normalized merchant keys, so we normalize
        incoming keys here as well.
        """

        normalized_user = self._normalize(user_id)

        self.user_rules[normalized_user] = {
            self._normalize(merchant): category
            for merchant, category in rules.items()
            if category in CATEGORIES
        }

    def add_user_rule(
        self,
        user_id: str,
        merchant: str,
        category: str,
    ) -> None:
        """
        Add or replace a user-specific categorization rule.

        This method only modifies the in-memory classifier.
        Persistence is handled by the database repository.
        """

        if category not in CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Expected one of: {', '.join(CATEGORIES)}"
            )

        normalized_user = self._normalize(user_id)
        normalized_merchant = self._normalize(merchant)

        self.user_rules.setdefault(normalized_user, {})[
            normalized_merchant
        ] = category

    def classify(
        self,
        transaction: TransactionRecord,
        user_id: str,
    ) -> CategoryResult:
        """
        Categorize one transaction.

        Returns an unmatched result when neither a user rule nor a
        deterministic system rule applies. The LLM fallback will be
        connected later.
        """

        merchant = self._normalize(transaction.merchant)
        description = self._normalize(transaction.description)
        normalized_user = self._normalize(user_id)

        # ---------------------------------------------------------
        # 1. USER-SPECIFIC RULE
        # ---------------------------------------------------------

        user_rule = self.user_rules.get(
            normalized_user,
            {},
        ).get(merchant)

        if user_rule is not None:
            return CategoryResult(
                category=user_rule,
                confidence=1.0,
                method="user_rule",
                matched_rule=merchant,
            )

        # ---------------------------------------------------------
        # 2. SYSTEM RULE
        # ---------------------------------------------------------

        searchable_text = f"{merchant} {description}"

        for rule in self.system_rules:
            for keyword in rule.merchant_keywords:
                normalized_keyword = self._normalize(keyword)

                if normalized_keyword in searchable_text:
                    return CategoryResult(
                        category=rule.category,
                        confidence=0.99,
                        method="system_rule",
                        matched_rule=normalized_keyword,
                    )

        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # 3. LLM FALLBACK
        # ---------------------------------------------------------

        if self.llm_fallback is not None:
            llm_result = self.llm_fallback.classify(
                merchant=transaction.merchant,
                description=transaction.description,
            )

            if llm_result is not None:
                category, confidence, explanation = llm_result

                return CategoryResult(
                    category=category,
                    confidence=confidence,
                    method="llm",
                    matched_rule=explanation,
                )

        # ---------------------------------------------------------
        # 4. UNMATCHED
        # ---------------------------------------------------------

        return CategoryResult(
            category="Other",
            confidence=0.0,
            method="unmatched",
            matched_rule=None,
        )

async def load_persisted_user_rules(
    categorizer: Categorizer,
    user_id: str,
) -> None:
    """
    Load a user's persisted merchant-category rules into the
    in-memory categorizer.

    Database access is kept outside Categorizer itself so the
    classifier remains easy to test.
    """

    rules = await get_user_category_rules(user_id)

    categorizer.load_user_rules(
        user_id=user_id,
        rules=rules,
    )