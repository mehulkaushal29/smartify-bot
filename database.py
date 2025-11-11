from tinydb import TinyDB, Query
from typing import Optional

DB_PATH = "users_db.json"
db = TinyDB(DB_PATH)
users = db.table("users")

DEFAULT_PREFS = {"jobs_au": False, "jobs_in": False, "ai_tools": False}

def get_user(user_id: int) -> dict:
    q = Query()
    row = users.get(q.user_id == user_id)
    if row:
        merged = {"user_id": user_id, "prefs": DEFAULT_PREFS.copy(), "tz": row.get("tz", "Australia/Melbourne")}
        merged["prefs"].update(row.get("prefs", {}))
        return merged
    return {"user_id": user_id, "prefs": DEFAULT_PREFS.copy(), "tz": "Australia/Melbourne"}

def upsert_user(user_id: int, prefs: Optional[dict] = None, tz: Optional[str] = None):
    q = Query()
    row = users.get(q.user_id == user_id)
    if row:
        new_prefs = row.get("prefs", {}).copy()
        if prefs:
            new_prefs.update(prefs)
        users.update({"prefs": new_prefs, "tz": tz or row.get("tz", "Australia/Melbourne")}, q.user_id == user_id)
    else:
        users.insert({"user_id": user_id, "prefs": prefs or DEFAULT_PREFS.copy(), "tz": tz or "Australia/Melbourne"})

def all_users():
    return users.all()
