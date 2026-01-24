from tinydb import TinyDB, Query
from typing import Optional

DB_PATH = "users_db.json"
db = TinyDB(DB_PATH)
users = db.table("users")


def get_user(user_id: int) -> dict:
    q = Query()
    row = users.get(q.user_id == user_id)
    if row:
        return row

    # default user
    user = {
        "user_id": user_id,
        "subscribed": False,
        "last_keyword": None,
        "last_location": None,
    }
    users.insert(user)
    return user


def upsert_user(
    user_id: int,
    subscribed: Optional[bool] = None,
    last_keyword: Optional[str] = None,
    last_location: Optional[str] = None,
):
    q = Query()
    row = users.get(q.user_id == user_id)

    data = row.copy() if row else {"user_id": user_id}

    if subscribed is not None:
        data["subscribed"] = subscribed
    if last_keyword is not None:
        data["last_keyword"] = last_keyword
    if last_location is not None:
        data["last_location"] = last_location

    if row:
        users.update(data, q.user_id == user_id)
    else:
        users.insert(data)


def all_users():
    return users.all()


def get_stats():
    all_u = users.all()
    total_users = len(all_u)
    subscribers = sum(1 for u in all_u if u.get("subscribed"))
    return total_users, subscribers
