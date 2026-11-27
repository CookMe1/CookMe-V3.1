import asyncio, sys
from types import SimpleNamespace
from mongomock_motor import AsyncMongoMockClient


def test_public_pages_and_sitemap_only_show_safe_recipes():
    sys.path.insert(0, "backend")
    import pytest
    from fastapi import HTTPException
    import routes.web_pages as wp

    base = dict(ingredients=[{"amount": "1 tbsp", "item": "oil"}], steps=["Cook it."], hidden_by=[], title="T", description="d",
                prep_time="1 hr 30 min", cook_time="15 min", servings="4", image="/recipe-images/a.jpg")

    async def run():
        db = AsyncMongoMockClient()["t"]
        await db.recipes.insert_many([
            {**base, "recipe_id": "pub", "user_id": "u1", "visibility": "public", "title": "Tom <b>&</b> Jerry", "public_author": "Sam"},
            {**base, "recipe_id": "wiki", "user_id": "system_seeder", "source_license": "CC BY-SA 4.0", "source_url": "https://en.wikibooks.org/wiki/x"},
            {**base, "recipe_id": "ai", "user_id": "system_seeder", "ai_generated": True},
            {**base, "recipe_id": "scraped", "user_id": "system_seeder", "source_url": "https://bbcgoodfood.com/x"},
            {**base, "recipe_id": "private", "user_id": "u1", "visibility": "private"},
            {**base, "recipe_id": "empty", "user_id": "u1", "visibility": "public", "steps": []},
        ])
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)), url=SimpleNamespace(scheme="https", netloc="x.test"))
        page = (await wp.public_recipe("pub", req)).body.decode()
        assert "Tom &lt;b&gt;&amp;&lt;/b&gt; Jerry" in page and "<b>&</b>" not in page      # escaped
        assert "application/ld+json" in page and "PT1H30M" in page and "https://x.test/recipe-images/a.jpg" in page
        assert "licensed CC BY-SA 4.0" in (await wp.public_recipe("wiki", req)).body.decode()
        assert (await wp.public_recipe("ai", req)).status_code == 200
        for rid in ("scraped", "private", "empty", "nope"):
            with pytest.raises(HTTPException):
                await wp.public_recipe(rid, req)
        xml = (await wp.sitemap(req)).body.decode()
        for rid in ("pub", "wiki", "ai"):
            assert f"/api/web/recipe/{rid}<" in xml
        for rid in ("scraped", "private"):
            assert f"/{rid}<" not in xml
    asyncio.run(run())
