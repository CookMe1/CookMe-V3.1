from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional
import uuid
from pydantic import BaseModel
from auth import get_current_user

router = APIRouter(prefix="/cookbooks", tags=["cookbooks"])


class CookbookCreate(BaseModel):
    name: str
    description: Optional[str] = None


# ── Get all cookbooks for the current user ────────────────────────────────────
@router.get("")
async def get_cookbooks(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    books = await db.cookbooks.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return books


# ── Create a cookbook ─────────────────────────────────────────────────────────
@router.post("")
async def create_cookbook(data: CookbookCreate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    doc = {
        "cookbook_id": f"cb_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "name": data.name.strip(),
        "description": data.description or "",
        "recipe_ids": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.cookbooks.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ── Delete a cookbook (recipes are NOT deleted) ───────────────────────────────
@router.delete("/{cookbook_id}")
async def delete_cookbook(cookbook_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    result = await db.cookbooks.delete_one(
        {"cookbook_id": cookbook_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cookbook not found")
    return {"message": "Cookbook deleted"}


# ── Add a recipe to a cookbook ────────────────────────────────────────────────
@router.post("/{cookbook_id}/recipes/{recipe_id}")
async def add_recipe_to_cookbook(cookbook_id: str, recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    result = await db.cookbooks.update_one(
        {"cookbook_id": cookbook_id, "user_id": user["user_id"]},
        {
            "$addToSet": {"recipe_ids": recipe_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cookbook not found")

    # Also store cookbook name on the recipe document for card display
    cookbook = await db.cookbooks.find_one({"cookbook_id": cookbook_id})
    if cookbook:
        await db.recipes.update_one(
            {"recipe_id": recipe_id},
            {"$set": {"cookbook": cookbook["name"], "cookbook_id": cookbook_id}},
        )

    return {"message": "Recipe added to cookbook"}


# ── Remove a recipe from a cookbook ──────────────────────────────────────────
@router.delete("/{cookbook_id}/recipes/{recipe_id}")
async def remove_recipe_from_cookbook(cookbook_id: str, recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    result = await db.cookbooks.update_one(
        {"cookbook_id": cookbook_id, "user_id": user["user_id"]},
        {
            "$pull": {"recipe_ids": recipe_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cookbook not found")

    # Clear cookbook field from recipe if it belonged to this book
    await db.recipes.update_one(
        {"recipe_id": recipe_id, "cookbook_id": cookbook_id},
        {"$unset": {"cookbook": "", "cookbook_id": ""}},
    )

    return {"message": "Recipe removed from cookbook"}


# ── Rename a cookbook ─────────────────────────────────────────────────────────
@router.patch("/{cookbook_id}")
async def rename_cookbook(cookbook_id: str, data: CookbookCreate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    result = await db.cookbooks.update_one(
        {"cookbook_id": cookbook_id, "user_id": user["user_id"]},
        {"$set": {"name": data.name.strip(), "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cookbook not found")
    return {"message": "Cookbook renamed"}
