#!/usr/bin/env python3
"""
Import data from a CookMe MongoDB JSON export (from the old Emergent project) into this app's database.

SAFE BY DEFAULT: without --apply nothing is written; it only prints what it would do.
Re-running is safe: documents that already exist are skipped, never overwritten or duplicated.

Examples (run from the project root, with MONGO_URL and DB_NAME set, or backend/.env present):
  python scripts/import_from_export.py export.json                        # lists the accounts in the file
  python scripts/import_from_export.py export.json --emails me@example.com            # dry run
  python scripts/import_from_export.py export.json --emails me@example.com --apply    # really import
  python scripts/import_from_export.py export.json --emails old@x.com --as new@x.com --apply
        (use --as if you sign in to the new app with a DIFFERENT email than the old account)

What is imported for the chosen accounts: their recipes, pantry items, shopping list, saved recipes,
cookbooks and meal plans. Shared seeded recipes (owners "system_seeder" and "daily_import") are
imported too unless you pass --skip-seeded. Password hashes are never copied.
Do NOT commit the export file to GitHub: it contains personal data.
"""
import argparse, json, os, re, sys
from datetime import datetime, timezone

SEEDED_OWNERS = {"system_seeder", "daily_import"}
SKIP_USER_FIELDS = {"_id", "password_hash", "verification_code"}


def convert(v):
    """Turn MongoDB extended JSON ($oid/$date) into plain Python values; drop nothing else."""
    if isinstance(v, dict):
        if set(v) == {"$oid"}:
            return v["$oid"]
        if set(v) == {"$date"}:
            s = v["$date"]
            if isinstance(s, str):
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            return datetime.fromtimestamp(s / 1000, tz=timezone.utc)
        return {k: convert(x) for k, x in v.items()}
    if isinstance(v, list):
        return [convert(x) for x in v]
    return v


def remap(v, m):
    """Replace old user ids with new ones anywhere inside a document (owner, favorited_by, gallery...)."""
    if not m:
        return v
    if isinstance(v, str):
        return m.get(v, v)
    if isinstance(v, list):
        return [remap(x, m) for x in v]
    if isinstance(v, dict):
        return {k: remap(x, m) for k, x in v.items()}
    return v


def mask(e):
    if not e:
        return "(no email)"
    a, _, b = e.partition("@")
    return a[:2] + "***@" + b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--emails", default="", help="comma-separated emails of the accounts to import")
    ap.add_argument("--all-users", action="store_true", help="import every account that has data")
    ap.add_argument("--as", dest="as_email", default="", help="import a single account into this other email")
    ap.add_argument("--skip-seeded", action="store_true", help="do not import the shared seeded recipes")
    ap.add_argument("--apply", action="store_true", help="actually write to the database")
    a = ap.parse_args()

    data = json.load(open(a.export, encoding="utf-8"))
    cols = {n: [convert(d) for d in c.get("documents", [])] for n, c in data["collections"].items()}
    users = cols.get("users", [])
    by_id = {u["user_id"]: u for u in users}

    owners = set()
    for n in ("recipes", "pantry_items", "shopping_lists", "recipe_saves", "cookbooks", "meal_plans"):
        owners |= {d.get("user_id") for d in cols.get(n, [])}
    owners -= SEEDED_OWNERS

    wanted = [e.strip().lower() for e in a.emails.split(",") if e.strip()]
    if not wanted and not a.all_users:
        print(f"Export from {data.get('database')} taken {data.get('exported_at_iso')}")
        print("Accounts that own data (choose with --emails or --all-users):")
        for uid in sorted(owners):
            u = by_id.get(uid)
            n = {k: sum(1 for d in cols.get(k, []) if d.get("user_id") == uid)
                 for k in ("recipes", "pantry_items", "shopping_lists", "recipe_saves", "cookbooks", "meal_plans")}
            print(f"  {mask(u.get('email')) if u else '(account record missing)'}  {uid}  {{{', '.join(f'{k}: {v}' for k, v in n.items() if v)}}}")
        sys.exit("\nNothing imported. Re-run with --emails you@example.com (dry run), then add --apply.")
    if a.as_email and (a.all_users or len(wanted) != 1):
        sys.exit("--as works with exactly one --emails address.")

    selected = []
    for uid in sorted(owners | set(by_id)):
        u = by_id.get(uid)
        if a.all_users and uid in owners and u:
            selected.append(u)
        elif u and (u.get("email") or "").lower() in wanted:
            selected.append(u)
    missing = [e for e in wanted if e not in {(u.get("email") or "").lower() for u in selected}]
    if missing:
        sys.exit("No account in the export with email: " + ", ".join(missing))

    try:
        from pymongo import MongoClient
    except ImportError:
        sys.exit("pip install pymongo")
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", ".env"))
    except ImportError:
        pass
    if not os.environ.get("MONGO_URL") or not os.environ.get("DB_NAME"):
        sys.exit("Set MONGO_URL and DB_NAME (or have backend/.env).")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    stats = {}

    def bump(name, key):
        stats.setdefault(name, {"new": 0, "already there": 0})[key] += 1

    def put(coll, filt, doc):
        """Insert only if no document matches filt. Never overwrites."""
        if db[coll].find_one(filt, {"_id": 1}):
            bump(coll, "already there")
            return
        bump(coll, "new")
        if a.apply:
            db[coll].update_one(filt, {"$setOnInsert": doc}, upsert=True)

    # 1) accounts: map old user ids to the ids that exist (or will exist) in this database
    idmap, selected_ids = {}, set()
    for u in selected:
        selected_ids.add(u["user_id"])
        target_email = a.as_email or u.get("email")
        existing = db.users.find_one({"email": {"$regex": "^" + re.escape(target_email) + "$", "$options": "i"}})
        doc = {k: v for k, v in remap(u, idmap).items() if k not in SKIP_USER_FIELDS}
        doc["email"] = target_email
        if existing:
            if existing["user_id"] != u["user_id"]:
                idmap[u["user_id"]] = existing["user_id"]
            bump("users", "already there")
            print(f"  account {mask(target_email)} already exists here -> data will be attached to it ({existing['user_id']})")
        else:
            put("users", {"user_id": doc["user_id"]}, doc)

    def wrap(d):
        d = {k: v for k, v in d.items() if k != "_id"}
        return remap(d, idmap)

    # 2) data
    for r in cols.get("recipes", []):
        if r.get("user_id") in selected_ids or (r.get("user_id") in SEEDED_OWNERS and not a.skip_seeded):
            d = wrap(r)
            put("recipes", {"recipe_id": d["recipe_id"]}, d)
    for p in cols.get("pantry_items", []):
        if p.get("user_id") in selected_ids:
            d = wrap(p)
            put("pantry_items", {"item_id": d["item_id"]}, d)
    for s in cols.get("shopping_lists", []):
        if s.get("user_id") in selected_ids:
            d = wrap(s)
            if db.shopping_lists.find_one({"user_id": d["user_id"]}, {"_id": 1}):
                bump("shopping_lists", "already there")  # keep the list they already have here
            else:
                put("shopping_lists", {"list_id": d["list_id"]}, d)
    for s in cols.get("recipe_saves", []):
        if s.get("user_id") in selected_ids:
            d = wrap(s)
            put("recipe_saves", {"recipe_id": d["recipe_id"], "user_id": d["user_id"]}, d)
    for coll, key in (("cookbooks", "cookbook_id"), ("meal_plans", "meal_plan_id")):
        for x in cols.get(coll, []):
            if x.get("user_id") in selected_ids:
                d = wrap(x)
                put(coll, {key: d[key]}, d)

    print(("APPLIED" if a.apply else "DRY RUN (nothing written)") + f" -> database {os.environ['DB_NAME']}")
    for coll, s in stats.items():
        print(f"  {coll:15s} new: {s['new']:5d}   already there: {s['already there']}")
    if not a.apply:
        print("\nLooks right? Run the same command again with --apply.")


if __name__ == "__main__":
    main()
