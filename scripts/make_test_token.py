#!/usr/bin/env python3
"""
Create (or reuse) a TEST user directly in MongoDB and print a JWT for scripts/smoke_test.py.
The app has no email/password login (social login only), so this is the way to get a token for testing.

  export MONGO_URL=... DB_NAME=... JWT_SECRET=...     # the SAME values the backend uses
  pip install pymongo "python-jose"
  python scripts/make_test_token.py
Only use against your own database. Never run it with a production secret on a shared machine.
"""
import os, sys, uuid
from datetime import datetime, timedelta, timezone
try:
    from pymongo import MongoClient
    from jose import jwt
except ImportError:
    sys.exit('pip install pymongo "python-jose"')
for k in ("MONGO_URL", "DB_NAME", "JWT_SECRET"):
    if not os.environ.get(k): sys.exit(f"Set {k}")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
email = "smoke-test@example.test"
u = db.users.find_one({"email": email})
if not u:
    u = {"user_id": f"user_{uuid.uuid4().hex[:12]}", "email": email, "name": "Smoke Test", "avatar": "", "bio": "",
         "auth_provider": "test", "is_food_blogger": False, "social_enabled": True, "followers_count": 0,
         "following_count": 0, "recipes_count": 0, "created_at": datetime.now(timezone.utc)}
    db.users.insert_one(u)
tok = jwt.encode({"sub": u["user_id"], "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                 os.environ["JWT_SECRET"], algorithm=os.environ.get("JWT_ALGORITHM", "HS256"))
print(tok)
