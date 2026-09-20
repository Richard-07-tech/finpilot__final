from app.intelligence.categorization.llm import LLMCategoryFallback


def test_llm_fallback_classifies_with_injected_provider():
    def fake_classifier(merchant, description):
        assert merchant == "unknown cafe"
        assert description == "upi payment"
        return "Food & Dining", 0.91, "Cafe merchant"

    fallback = LLMCategoryFallback(fake_classifier)

    result = fallback.classify(
        merchant="unknown cafe",
        description="upi payment",
    )

    assert result is not None
    assert result[0] == "Food & Dining"
    assert result[1] == 0.91
    assert result[2] == "Cafe merchant"


def test_llm_fallback_returns_none_without_provider():
    fallback = LLMCategoryFallback(classifier=None)
    fallback.client = None

    assert fallback.client is None
