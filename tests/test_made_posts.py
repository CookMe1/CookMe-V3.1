import asyncio, base64, io, sys
from types import SimpleNamespace
import pytest
from mongomock_motor import AsyncMongoMockClient
from fastapi import HTTPException


def _photo():
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (1600, 1200), (200, 120, 40)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_made_it_posts_work_on_library_recipes_and_are_moderated():
    sys.path.insert(0, "backend")
    import routes.social_routes as sr

    async def run():
        db = AsyncMongoMockClient()["t"]
        await db.recipes.insert_one({"recipe_id": "lib1", "user_id": "system_seeder", "title": "Cowboy Butter Chicken", "hidden_by": []})
        await db.recipes.insert_one({"recipe_id": "priv1", "user_id": "someone_else", "title": "Secret", "visibility": "private", "hidden_by": []})
        users = {"u1": {"user_id": "u1", "name": "Kabir Patel"}, "u2": {"user_id": "u2", "name": "Sam Lee"}}
        current = {"u": "u1"}
        sr.get_current_user = lambda request, db: asyncio.sleep(0, users[current["u"]])
        sr.notify.alert_admin = lambda *a, **k: asyncio.sleep(0)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))

        # a library recipe (not owned by the person) can be posted about
        post = await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="Loved it!", image_data=_photo()), req)
        assert post["recipe_title"] == "Cowboy Butter Chicken" and post["author_name"] == "Kabir P." and post["mine"]
        stored = await db.made_posts.find_one({"post_id": post["post_id"]})
        assert len(stored["photo"]) < 200_000                                    # shrunk, not the full upload
        # someone else's private recipe is not visible, so no post
        with pytest.raises(HTTPException) as e: await sr.post_made_it(sr.MadeIn(recipe_id="priv1", note="", image_data=_photo()), req)
        assert e.value.status_code == 404
        # links are refused, a photo is required, bad data is refused
        with pytest.raises(HTTPException) as e: await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="see www.example.com", image_data=_photo()), req)
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e: await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="x", image_data=""), req)
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e: await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="x", image_data="data:image/png;base64,AAAA"), req)
        assert e.value.status_code == 400

        # everyone can see it; the photo is served; the list never carries the image bytes
        current["u"] = "u2"
        listing = await sr.list_made(req, recipe_id="lib1")
        assert [p["post_id"] for p in listing["posts"]] == [post["post_id"]] and not listing["posts"][0]["mine"]
        assert "photo" not in listing["posts"][0]
        resp = await sr.made_photo(post["post_id"], req)
        assert resp.media_type == "image/jpeg" and resp.body[:2] == b"\xff\xd8"

        # reporting: owner can't report own, three reports hide it, then the photo is no longer served
        await sr.report_made(post["post_id"], sr.ReportIn(reason="other"), req)
        for uid in ("u3", "u4"):
            users[uid] = {"user_id": uid, "name": "R " + uid}; current["u"] = uid
            await sr.report_made(post["post_id"], sr.ReportIn(reason="other"), req)
        assert (await db.made_posts.find_one({"post_id": post["post_id"]}))["status"] == "hidden"
        with pytest.raises(HTTPException) as e: await sr.made_photo(post["post_id"], req)
        assert e.value.status_code == 404
        assert (await sr.list_made(req))["posts"] == []

        # only the owner can delete; daily limit applies
        current["u"] = "u1"
        p2 = await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="again", image_data=_photo()), req)
        current["u"] = "u2"
        with pytest.raises(HTTPException) as e: await sr.delete_made(p2["post_id"], req)
        assert e.value.status_code == 403
        current["u"] = "u1"
        await sr.delete_made(p2["post_id"], req)
        for _ in range(sr.MAX_MADE_PER_DAY - 1):                 # the first post already counts
            await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="n", image_data=_photo()), req)
        with pytest.raises(HTTPException) as e: await sr.post_made_it(sr.MadeIn(recipe_id="lib1", note="n", image_data=_photo()), req)
        assert e.value.status_code == 429
    asyncio.run(run())
