#!/usr/bin/env python3
"""Estimate amounts for recipes whose ingredient list has none (about 430 Wikibooks recipes).
Needs the Emergent LLM key (so it costs credits): run on Emergent, or anywhere with EMERGENT_LLM_KEY set.
  python scripts/ai_fill_amounts.py data/staging/wikibooks_needs_amounts.json [--limit 50] [--dry]
For each recipe the AI is told to ADD a sensible quantity to ingredients that have none, using the servings and method, and to
change nothing else. Every recipe it touches is flagged amounts_estimated = true and needs_review = true, so it goes through your
admin review before anyone sees it. The reply is checked: same ingredient names in the same order, otherwise the recipe is left alone."""
import asyncio, json, re, sys, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from ai_client import model_for


def build_prompt(r):
    lines = "\n".join(f"{n}. {(i.get('amount') or '').strip()} | {i.get('item', '')}" for n, i in enumerate(r["ingredients"], 1))
    steps = " ".join(str(s) for s in r["steps"])[:1500]
    return (f"Recipe: {r['title']} (serves {r.get('servings', 4)})\nIngredients as 'amount | item' (some amounts are missing):\n{lines}\n\n"
            f"Method: {steps}\n\nFor every ingredient with an empty amount, give a sensible quantity for this many servings "
            "(metric where possible, e.g. '200 g', '2 tbsp', '1 medium'; use 'to taste' only for salt, pepper and seasonings). "
            "Keep amounts that already exist exactly as they are. Do not add, remove, rename or reorder ingredients. "
            "Reply with JSON only: a list of objects {\"amount\": ..., \"item\": ...} in the same order.")


def valid(original, new):
    if not isinstance(new, list) or len(new) != len(original):
        return False
    for o, n in zip(original, new):
        if not isinstance(n, dict) or str(n.get("item", "")).strip().lower() != str(o.get("item", "")).strip().lower():
            return False
        if (o.get("amount") or "").strip() and str(n.get("amount", "")).strip() != o["amount"].strip():
            return False
        if not str(n.get("amount", "")).strip():
            return False
    return True


async def ask(r):
    import os
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"amt_{uuid.uuid4().hex[:8]}",
                   system_message="You complete recipe ingredient quantities accurately and conservatively.").with_model(*model_for())
    text = await asyncio.wait_for(chat.send_message(UserMessage(text=build_prompt(r))), timeout=40)
    m = re.search(r"\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else None


async def main():
    path = ROOT / sys.argv[1]
    rows = json.loads(path.read_text(encoding="utf-8"))
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else len(rows)
    done = skipped = 0
    for r in rows[:limit]:
        if r.get("amounts_estimated"):
            continue
        try:
            new = await ask(r)
        except Exception as e:
            print("  skip", r["title"], e); skipped += 1; continue
        if not valid(r["ingredients"], new):
            print("  reply did not match, left alone:", r["title"]); skipped += 1; continue
        if "--dry" not in sys.argv:
            r["ingredients"] = [{**o, "amount": str(n["amount"]).strip()} for o, n in zip(r["ingredients"], new)]
            r["amounts_estimated"] = True; r["needs_review"] = True
        done += 1
        if done % 10 == 0 and "--dry" not in sys.argv:
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    if "--dry" not in sys.argv:
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"{done} recipes got estimated amounts, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(main())
