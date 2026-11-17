from fastapi import APIRouter, Request
from datetime import datetime, timezone
from typing import List, Optional
import uuid
import os
from pydantic import BaseModel
from auth import get_current_user
from cache import get_aisle, set_aisle
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")


class ShoppingItem(BaseModel):
    item_id: Optional[str] = None
    name: str
    amount: Optional[str] = "1"
    checked: Optional[bool] = False
    category: Optional[str] = "Other"


class ShoppingListUpdate(BaseModel):
    items: List[dict]


# Get shopping list
@router.get("")
async def get_shopping_list(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    shopping_list = await db.shopping_lists.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not shopping_list:
        # Create empty shopping list
        shopping_list = {
            "list_id": f"list_{uuid.uuid4().hex[:12]}",
            "user_id": user["user_id"],
            "items": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.shopping_lists.insert_one(shopping_list)
        shopping_list.pop("_id", None)
    
    return shopping_list

# Update shopping list
@router.put("")
async def update_shopping_list(list_data: ShoppingListUpdate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    await db.shopping_lists.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "items": list_data.items,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    return {"message": "Shopping list updated"}

# Clear shopping list
@router.delete("")
async def clear_shopping_list(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    await db.shopping_lists.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "items": [],
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"message": "Shopping list cleared"}


class AddItemsRequest(BaseModel):
    items: List[str]  # List of ingredient names to add


class AisleRequest(BaseModel):
    name: str  # Single ingredient name


# ── Assign aisle to a single item (cache-first, AI fallback) ──────────────────
@router.post("/assign-aisle")
async def assign_aisle(body: AisleRequest, request: Request):
    """
    Return the supermarket aisle for an ingredient.
    Checks in-memory table → MongoDB cache → AI (and caches result).
    This means 'chicken breast' is never sent to the AI twice.
    """
    db = request.app.state.db
    await get_current_user(request, db)

    # 1. Check cache (memory table + MongoDB)
    aisle = await get_aisle(db, body.name)
    if aisle:
        return {"name": body.name, "aisle": aisle, "cached": True}

    # 2. Not cached — ask AI
    try:
        import json, re
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"aisle_{uuid.uuid4().hex[:8]}",
            system_message="You assign grocery store aisles to ingredients. Return ONLY valid JSON."
        ).with_model("openai", "gpt-4o-mini")

        prompt = f"""Which supermarket aisle does "{body.name}" belong to?

Choose exactly one from this list:
Produce, Meat & Seafood, Dairy, Bakery, Grains, Canned, Frozen, Spices, Oils, Condiments, Baking, Beverages, Snacks, Other

Return ONLY: {{"aisle": "Aisle Name"}}"""

        response_text = await chat.send_message(UserMessage(text=prompt))
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        result = json.loads(match.group() if match else response_text)
        aisle = result.get("aisle", "Other")

        # 3. Cache the result permanently
        await set_aisle(db, body.name, aisle)

        return {"name": body.name, "aisle": aisle, "cached": False}

    except Exception:
        return {"name": body.name, "aisle": "Other", "cached": False}


# ── Add multiple items to shopping list (cache-aware aisle assignment) ─────────
@router.post("/add-items")
async def add_items_to_shopping_list(request_data: AddItemsRequest, request: Request):
    """
    Add multiple items to the shopping list.
    Aisle is resolved from cache (memory → MongoDB → AI) for each item,
    so AI is only called for items we've never seen before.
    """
    db = request.app.state.db
    user = await get_current_user(request, db)

    # Get or create shopping list
    shopping_list = await db.shopping_lists.find_one({"user_id": user["user_id"]})
    if not shopping_list:
        shopping_list = {
            "list_id": f"list_{uuid.uuid4().hex[:12]}",
            "user_id": user["user_id"],
            "items": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.shopping_lists.insert_one(shopping_list)

    existing_items = shopping_list.get("items", [])
    existing_names = {item.get("name", "").lower() for item in existing_items}

    new_items = []
    for item_name in request_data.items:
        if item_name.lower() in existing_names:
            continue

        # Resolve aisle from cache — no AI call for known items
        aisle = await get_aisle(db, item_name)
        if not aisle:
            # Unknown item — call AI once and cache
            try:
                import json, re
                chat = LlmChat(
                    api_key=EMERGENT_KEY,
                    session_id=f"aisle_{uuid.uuid4().hex[:8]}",
                    system_message="You assign grocery store aisles to ingredients. Return ONLY valid JSON."
                ).with_model("openai", "gpt-4o-mini")
                prompt = f"""Which supermarket aisle does "{item_name}" belong to?
Choose from: Produce, Meat & Seafood, Dairy, Bakery, Grains, Canned, Frozen, Spices, Oils, Condiments, Baking, Beverages, Snacks, Other
Return ONLY: {{"aisle": "Aisle Name"}}"""
                resp = await chat.send_message(UserMessage(text=prompt))
                m = re.search(r'\{.*\}', resp, re.DOTALL)
                aisle = json.loads(m.group() if m else resp).get("aisle", "Other")
                await set_aisle(db, item_name, aisle)
            except Exception:
                aisle = "Other"

        new_items.append({
            "item_id": f"item_{uuid.uuid4().hex[:8]}",
            "name": item_name,
            "category": aisle,
            "checked": False,
            "added_at": datetime.now(timezone.utc).isoformat()
        })
        existing_names.add(item_name.lower())

    if new_items:
        await db.shopping_lists.update_one(
            {"user_id": user["user_id"]},
            {
                "$push": {"items": {"$each": new_items}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

    return {
        "message": f"Added {len(new_items)} items to shopping list",
        "added_count": len(new_items),
        "skipped_count": len(request_data.items) - len(new_items)
    }