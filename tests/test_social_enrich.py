import asyncio, sys
sys.path.insert(0, "backend")
import social_enrich as se


def test_find_links_skips_social_and_shops():
    text = ("Full recipe: https://www.example-kitchen.com/recipes/creamy-pasta?utm=1 !! follow https://instagram.com/me "
            "buy https://amzn.to/abc and https://linktr.ee/me. Also see bbcgoodfood.com/recipes/easy-pancakes")
    links = se.find_links(text)
    assert links[0].startswith("https://www.example-kitchen.com/recipes/creamy-pasta")
    assert all("instagram" not in u and "amzn" not in u and "linktr" not in u for u in links)
    assert any("bbcgoodfood.com/recipes/easy-pancakes" in u for u in links)


def test_recipe_like_comment_detection():
    recipe = "Ingredients:\n2 cups flour\n1 tsp salt\n200 g butter\n3 cloves garlic\nMethod: mix everything"
    assert se.looks_like_recipe_text(recipe)
    assert not se.looks_like_recipe_text("Looks so good!! Can't wait to try this one tonight, thank you for sharing")
    assert not se.looks_like_recipe_text("I use 2 cups of coffee a day")


def test_pick_useful_comments_prefers_author_and_links():
    comments = [
        {"text": "yum", "likes": 500, "by_author": False},
        {"text": "Recipe on my blog https://myblog.com/recipes/stew", "likes": 3, "by_author": True},
        {"text": "Ingredients:\n2 cups rice\n1 tsp salt\n200 g chicken thighs\n3 cloves garlic\nMethod: brown the chicken, add the rice and water, cook 20 minutes", "likes": 9, "by_author": False},
    ]
    links, text = se.pick_useful_comments(comments)
    assert links == ["https://myblog.com/recipes/stew"]
    assert "2 cups rice" in text and "yum" not in text


def test_look_in_comments_follows_link_in_comment(monkeypatch):
    async def fake_details(video_id):
        return {"description": "", "channel_id": "c", "comments": [
            {"text": "Full recipe https://myblog.com/recipes/stew", "likes": 1, "by_author": True}]}

    async def fake_recipe(links, limit=3):
        return ({"title": "Stew", "ingredients": [{"item": "beef"}], "steps": ["cook"]}, links[0]) if links else (None, None)

    monkeypatch.setattr(se, "youtube_details", fake_details)
    monkeypatch.setattr(se, "recipe_from_links", fake_recipe)
    res = asyncio.run(se.look_in_comments("youtube", "https://youtu.be/abcdefghijk", "no links here", "abcdefghijk"))
    assert res["found_via"] == "link in the comments" and res["recipe"]["title"] == "Stew" and res["comments_checked"]


def test_platforms_without_comment_access_are_not_faked():
    res = asyncio.run(se.look_in_comments("tiktok", "https://tiktok.com/x", "yummy pasta"))
    assert res["recipe"] is None and res["comments_checked"] is False and res["comment_text"] == ""
