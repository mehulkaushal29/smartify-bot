from tinydb import TinyDB, Query
from typing import Optional, Dict, Any

DB_PATH = "users_db.json"
db = TinyDB(DB_PATH)
users = db.table("users")

DEFAULT_PREFS = {"jobs_au": False, "jobs_in": False, "ai_tools": False}

def get_user(user_id: int) -> dict:
    q = Query()
    row = users.get(q.user_id == user_id)

    base = {
        "user_id": user_id,
        "prefs": DEFAULT_PREFS.copy(),
        "tz": "Australia/Melbourne",
        "subscribed": False,
        "last_keyword": "jobs",
        "last_location": None,
    }

    if not row:
        return base

    # merge prefs safely
    prefs = DEFAULT_PREFS.copy()
    prefs.update(row.get("prefs", {}) or {})

    base.update({
        "prefs": prefs,
        "tz": row.get("tz", base["tz"]),
        "subscribed": row.get("subscribed", base["subscribed"]),
        "last_keyword": row.get("last_keyword", base["last_keyword"]),
        "last_location": row.get("last_location", base["last_location"]),
    })

    return base


def upsert_user(
    user_id: int,
    prefs: Optional[dict] = None,
    tz: Optional[str] = None,
    subscribed: Optional[bool] = None,
    last_keyword: Optional[str] = None,
    last_location: Optional[str] = None,
):
    q = Query()
    row = users.get(q.user_id == user_id)

    if row:
        update_doc: Dict[str, Any] = {}

        # prefs merge
        if prefs is not None:
            new_prefs = (row.get("prefs") or {}).copy()
            new_prefs.update(prefs)
            update_doc["prefs"] = new_prefs

        if tz is not None:
            update_doc["tz"] = tz

        if subscribed is not None:
            update_doc["subscribed"] = subscribed

        if last_keyword is not None:
            update_doc["last_keyword"] = last_keyword

        if last_location is not None:
            update_doc["last_location"] = last_location

        if update_doc:
            users.update(update_doc, q.user_id == user_id)

    else:
        users.insert({
            "user_id": user_id,
            "prefs": prefs or DEFAULT_PREFS.copy(),
            "tz": tz or "Australia/Melbourne",
            "subscribed": bool(subscribed) if subscribed is not None else False,
            "last_keyword": last_keyword or "jobs",
            "last_location": last_location,
        })


def all_users():
    return users.all()
