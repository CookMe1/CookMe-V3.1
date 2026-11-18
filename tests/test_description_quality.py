import asyncio
import pytest
import description_quality as dq


@pytest.mark.parametrize("desc,weak", [
    ("", True), ("Tasty", True), ("Spanish Tortilla", True),
    ("A delicious lamb recipe from Vietnamese cuisine.", True),
    ("A Spanish dish made with onion, potatoes and garlic.", True),
    ("Subscribe to my channel and follow me on Instagram for more recipes every week!", True),
    ("Visit https://example.com for the full recipe and a lot more great ideas here", True),
    ("Slow-braised lamb shanks in a fragrant star anise broth, finished with fresh herbs and lime.", False),
    ("Elegant and striking, this recipe transforms humble green beans into the star of the table.", False),
])
def test_weak_detection(desc, weak):
    assert dq.description_is_weak(desc, "Spanish Tortilla") is weak


def test_ai_description_used_when_good_and_fallback_otherwise(monkeypatch):
    recipe = {"title": "Tortilla", "cuisine": "spanish", "ingredients": [{"item": "Eggs"}, {"item": "Potatoes"}, {"item": "Onion"}]}

    async def good(r): return '"A thick, golden Spanish omelette of tender potatoes and sweet onion, set with eggs and served warm or cold."'
    monkeypatch.setattr(dq, "_ask_llm", good)
    text, src = asyncio.run(dq.improved_description(recipe))
    assert src == "ai" and text.startswith("A thick") and '"' not in text

    async def chatty(r): return "Sure, here is a description: it is nice."
    monkeypatch.setattr(dq, "_ask_llm", chatty)
    assert asyncio.run(dq.improved_description(recipe))[1] == "auto"

    async def boom(r): raise RuntimeError("no key")
    monkeypatch.setattr(dq, "_ask_llm", boom)
    text, src = asyncio.run(dq.improved_description(recipe))
    assert src == "auto" and "eggs" in text.lower()
