from tinydb import TinyDB, Query

db = TinyDB("users_db.json")
users = db.table("users")
User = Query()

def get_user(user_id: int) -> dict:
    user = users.get(User.user_id == user_id)
    if not user:
        user = {
            "user_id": user_id,
            "subscribed": False,
            "last_keyword": None,
            "last_location": None,
            "tz": "Australia/Melbourne"
        }
        users.insert(user)
    return user

def upsert_user(
    user_id: int,
    subscribed: bool = None,
    last_keyword: str = None,
    last_location: str = None,
    tz: str = None
):
    user = get_user(user_id)
    update = {}

    if subscribed is not None:
        update["subscribed"] = subscribed
    if last_keyword:
        update["last_keyword"] = last_keyword
    if last_location:
        update["last_location"] = last_location
    if tz:
        update["tz"] = tz

    users.update(update, User.user_id == user_id)

def all_users():
    return users.all()
