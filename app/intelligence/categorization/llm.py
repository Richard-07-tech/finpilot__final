import json
import os
from collections.abc import Callable

from dotenv import load_dotenv
from google import genai

from app.intelligence.categorization.rules import CATEGORIES, validate_category

LLMClassifier = Callable[[str, str], tuple[str, float, str]]

load_dotenv()


class LLMCategoryFallback:
    def __init__(self, classifier: LLMClassifier | None = None) -> None:
        self.classifier = classifier

        if classifier is None:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")

            self.client = genai.Client(api_key=api_key)

    def classify(
        self,
        merchant: str,
        description: str,
    ) -> tuple[str, float, str] | None:

        if self.classifier is not None:
            category, confidence, explanation = self.classifier(
                merchant,
                description,
            )

            category = validate_category(category)
            confidence = max(0.0, min(1.0, float(confidence)))

            return category, confidence, explanation

        prompt = f"""
Classify this financial transaction into exactly one category.

Allowed categories:
{", ".join(CATEGORIES)}

Merchant: {merchant}
Description: {description}

Return JSON only:
{{
  "category": "<allowed category>",
  "confidence": 0.0,
  "explanation": "brief evidence-based reason"
}}

Do not provide financial advice.
"""

        if not hasattr(self, "_cache"):
            self._cache: dict[str, tuple[str, float, str]] = {}
        if not hasattr(self, "_rate_limited"):
            self._rate_limited = False

        cache_key = f"{merchant.strip().lower()}:{description.strip().lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._rate_limited:
            return "Other", 0.0, "LLM rate limited, defaulted to Other"

        if not hasattr(self, "client") or self.client is None:
            return "Other", 0.0, "No LLM client configured"

        configured_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        candidate_models = list(dict.fromkeys([configured_model, "gemini-flash-latest", "gemini-3-flash-preview", "gemini-flash-lite-latest"]))

        last_exc = None
        for model_name in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                data = json.loads(response.text)

                category = validate_category(data["category"])
                confidence = max(
                    0.0,
                    min(1.0, float(data["confidence"])),
                )
                explanation = str(data.get("explanation", ""))

                result = (category, confidence, explanation)
                self._cache[cache_key] = result
                return result
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    self._rate_limited = True
                    break
                continue

        return "Other", 0.0, f"LLM classification failed: {last_exc}"

    @staticmethod
    def allowed_categories_prompt() -> str:
        return "Allowed categories: " + ", ".join(CATEGORIES)
