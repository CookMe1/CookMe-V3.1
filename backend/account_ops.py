"""Lock / reinstate / erase / ban accounts. Used by account deletion, reporting and the admin review queue."""
from datetime import datetime, timezone

USER_DATA = ["recipes", "pantry_items", "shopping_list", "shopping_lists", "cookbooks", "meal_plans",
             "recipe_saves", "recipe_likes", "community_likes", "comments"]


async def erase_user_content(db, uid: str):
    """Delete everything a user created (and replies under their comments). Consent records stay as proof of licence."""
    mine = await db.comments.find({"user_id": uid}, {"_id": 0, "comment_id": 1}).to_list(100000)
    if mine:
        await db.comments.delete_many({"parent_id": {"$in": [c["comment_id"] for c in mine]}})
    for name in USER_DATA:
        await db[name].delete_many({"user_id": uid})
    await db.recipe_consents.update_many({"user_id": uid}, {"$set": {"account_deleted_at": datetime.now(timezone.utc)}})
    await db.user_sessions.delete_many({"user_id": uid})


async def lock_user(db, uid: str):
    """Put the account under review: they see a 'under review' page, and what they shared is hidden until a decision."""
    await db.users.update_one({"user_id": uid}, {"$set": {"status": "under_review", "review_started_at": datetime.now(timezone.utc)}})
    await db.recipes.update_many({"user_id": uid, "visibility": "public"},
                                 {"$set": {"visibility": "private", "publish_status": "under_review", "held_by_review": True}})
    await db.comments.update_many({"user_id": uid, "status": "visible"}, {"$set": {"status": "hidden", "held_by_review": True}})


async def unlock_user(db, uid: str):
    await db.users.update_one({"user_id": uid}, {"$set": {"status": "active"}, "$unset": {"review_started_at": ""}})
    await db.recipes.update_many({"user_id": uid, "held_by_review": True},
                                 {"$set": {"visibility": "public", "publish_status": "public"}, "$unset": {"held_by_review": ""}})
    await db.comments.update_many({"user_id": uid, "held_by_review": True},
                                  {"$set": {"status": "visible"}, "$unset": {"held_by_review": ""}})


async def ban_user(db, uid: str):
    """Delete their content and block the account and its email address from signing in again."""
    user = await db.users.find_one({"user_id": uid}, {"_id": 0}) or {}
    await erase_user_content(db, uid)
    email = (user.get("email") or "").lower()
    if email:
        await db.banned_emails.update_one({"email": email}, {"$set": {"email": email, "banned_at": datetime.now(timezone.utc)}}, upsert=True)
    await db.users.update_one({"user_id": uid}, {"$set": {"status": "banned", "name": "Closed account", "avatar": "", "bio": "",
                                                           "banned_at": datetime.now(timezone.utc)}})
