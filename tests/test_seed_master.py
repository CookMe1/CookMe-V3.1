import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from mongomock_motor import AsyncMongoMockClient
import seed_master

def run(c): return asyncio.new_event_loop().run_until_complete(c)

def make(tmp_path, n=3):
    f = tmp_path / "m.json"
    f.write_text(json.dumps([{"recipe_id": f"r{i}", "title": f"T{i}", "user_id": "system_seeder"} for i in range(n)]))
    return f

def test_seeds_empty_database_once(tmp_path):
    db = AsyncMongoMockClient()["t"]; f = make(tmp_path)
    assert run(seed_master.seed_master_recipes(db, f)) == 3
    assert run(db.recipes.count_documents({"user_id": "system_seeder"})) == 3
    run(db.recipes.delete_one({"recipe_id": "r1"}))                    # an admin removes one
    assert run(seed_master.seed_master_recipes(db, f)) == 0            # not brought back
    assert run(db.recipes.count_documents({})) == 2

def test_does_not_touch_users_and_can_be_disabled(tmp_path, monkeypatch):
    db = AsyncMongoMockClient()["t"]; f = make(tmp_path)
    monkeypatch.setenv("AUTO_SEED_MASTER", "0")
    assert run(seed_master.seed_master_recipes(db, f)) == 0
    monkeypatch.delenv("AUTO_SEED_MASTER")
    run(db.recipes.insert_one({"recipe_id": "mine", "user_id": "u1"}))   # a user recipe doesn't count as master
    assert run(seed_master.seed_master_recipes(db, f)) == 3

def test_real_file_is_valid():
    data = json.loads(seed_master.DATA.read_text(encoding="utf-8"))
    assert len(data) > 1000 and all(r.get("recipe_id") and r.get("title") for r in data)
