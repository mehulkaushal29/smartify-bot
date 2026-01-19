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
        # ✅ new fields (safe defaults)
        "subscribed": False,
        "last_keyword": None,
        "last_location": None,
    }

    if not row:
        return base

    # merge prefs
    merged_prefs = DEFAULT_PREFS.copy()
    merged_prefs.update(row.get("prefs", {}) or {})

    base.update(row)  # bring any stored fields
    base["prefs"] = merged_prefs
    base["tz"] = row.get("tz", "Australia/Melbourne")
    base["subscribed"] = bool(row.get("subscribed", False))
    base["last_keyword"] = row.get("last_keyword")
    base["last_location"] = row.get("last_location")

    return base


def upsert_user(
    user_id: int,
    prefs: Optional[dict] = None,
    tz: Optional[str] = None,
    subscribed: Optional[bool] = None,
    last_keyword: Optional[str] = None,
    last_location: Optional[str] = None,
    **extra: Any,
):
    """
    ✅ Backwards compatible:
    - You can still call: upsert_user(user_id, prefs=..., tz=...)
    ✅ New capabilities:
    - upsert_user(user_id, subscribed=True)
    - upsert_user(user_id, last_keyword="nurse", last_location="india")
    - Stores any extra keyword fields via **extra
    """
    q = Query()
    row = users.get(q.user_id == user_id)

    # build patch update object
    patch: Dict[str, Any] = {}

    # prefs merge
    if prefs is not None:
        existing_prefs = (row.get("prefs", {}) if row else {}) or {}
        new_prefs = existing_prefs.copy()
        new_prefs.update(prefs)
        patch["prefs"] = new_prefs

    # tz update
    if tz is not None:
        patch["tz"] = tz
    elif not row:
        patch["tz"] = "Australia/Melbourne"

    # new fields
    if subscribed is not None:
        patch["subscribed"] = bool(subscribed)

    if last_keyword is not None:
        patch["last_keyword"] = last_keyword

    if last_location is not None:
        patch["last_location"] = last_location

    # allow future expansion
    if extra:
        patch.update(extra)

    if row:
        if patch:
            users.update(patch, q.user_id == user_id)
    else:
        # create new record with defaults
        record = {
            "user_id": user_id,
            "prefs": DEFAULT_PREFS.copy(),
            "tz": "Australia/Melbourne",
            "subscribed": False,
            "last_keyword": None,
            "last_location": None,
        }
        # apply any initial patch values
        record.update(patch)
        users.insert(record)


def all_users():
    # ✅ FIX: remove trailing comma so this returns a list, not a tuple
    return users.all()
