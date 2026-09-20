from __future__ import annotations

from app.intelligence.models import CATEGORIES

def build_prompt(merchant: str, description: str) -> str:
    categories = ", ".join(CATEGORIES)
    return f'''You classify a financial transaction into exactly one category.\nAllowed categories: {categories}\n\nMerchant: {merchant}\nDescription: {description}\n\nReturn JSON only: {{"category":"<allowed category>","confidence":0.0,"explanation":"brief evidence-based reason"}}\nDo not invent categories. Do not provide financial advice.'''
