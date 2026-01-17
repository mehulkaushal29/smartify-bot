import logging
import re
from datetime import time as dtime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, DEFAULT_TZ, DAILY_HOUR, DAILY_MINUTE, CHANNEL_ID
from jobs_api import get_jobs
from ai_tools import get_ai_tools
from database import get_user, upsert_user, all_users
from utils import WELCOME, format_jobs, format_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartify")

# ----------------- COUNTRY PARSER -----------------

COUNTRY_MAP = {
    "australia": "AU",
    "india": "IN",
    "china": "CN",
    "singapore": "SG",
    "uae": "AE",
    "new zealand": "NZ",
    "usa": "US",
    "united states": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "canada": "CA",
    "germany": "DE",
    "france": "FR",
}

STOP_WORDS = {"in", "for", "at", "jobs", "job", "roles", "role"}

def parse_free_text_to_query(text: str):
    text = (text or "").lower().strip()
    text = re.sub(r"[,\.;:]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    country = None
    for name, code in sorted(COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{name}\b", text):
            country = code
            text = re.sub(rf"\b{name}\b", "", text).strip()
            break

    if not country:
        country = "AU"  # default only if user didn't specify

    tokens = [t for t in text.split() if t not in STOP_WORDS]
    keyword = " ".join(tokens).strip() or "software engineer"

    return keyword, country, None

# ----------------- UI HELPERS -----------------

def start_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔔 Subscribe for Daily Jobs", callback_data="ui:open_subscribe")]]
    )

def build_subscribe_keyboard(prefs: dict, daily_time: str):
    def label(key, text):
        return f"{'✅' if prefs.get(key) else '⭕️'} {text}"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(label("jobs_au", "Jobs AU"), callback_data="sub:toggle:jobs_au"),
            InlineKeyboardButton(label("jobs_in", "Jobs IN"), callback_data="sub:toggle:jobs_in"),
        ],
        [
            InlineKeyboardButton(label("ai_tools", "AI Tools"), callback_data="sub:toggle:ai_tools"),
        ],
        [
            InlineKeyboardButton("✅ Save", callback_data="sub:done"),
            InlineKeyboardButton("🛑 Unsubscribe", callback_data="sub:clear"),
        ],
        [
            InlineKeyboardButton(f"⏰ Daily at {daily_time}", callback_data="sub:nop")
        ]
    ])

# ----------------- COMMANDS -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user.id)
    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    prefs = user.get("prefs", {})
    daily_time = f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"

    await update.message.reply_text(
        "Choose what you want daily:",
        reply_markup=build_subscribe_keyboard(prefs, daily_time),
        parse_mode=ParseMode.HTML,
    )

async def sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    user = get_user(user_id)
    prefs = user.get("prefs", {"jobs_au": False, "jobs_in": False, "ai_tools": False})

    if q.data == "ui:open_subscribe":
        return await q.edit_message_text(
            "Choose what you want daily:",
            reply_markup=build_subscribe_keyboard(
                prefs, f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"
            ),
            parse_mode=ParseMode.HTML,
        )

    if q.data == "sub:clear":
        upsert_user(user_id, prefs={"jobs_au": False, "jobs_in": False, "ai_tools": False})
        return await q.edit_message_text("Unsubscribed from all.")

    if q.data == "sub:done":
        upsert_user(user_id, prefs=prefs)
        return await q.edit_message_text("✅ Preferences saved.")

    if q.data.startswith("sub:toggle:"):
        key = q.data.split(":")[-1]
        prefs[key] = not prefs.get(key)
        return await q.edit_message_reply_markup(
            reply_markup=build_subscribe_keyboard(
                prefs, f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"
            )
        )

# ----------------- TEXT SEARCH (MAIN FIX) -----------------

async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kw, cc, _ = parse_free_text_to_query(update.message.text)

    results = get_jobs(kw, cc)

    header = f"🔎 <b>Jobs for “{kw}” — {cc}</b>"

    if not results:
        msg = (
            f"{header}\n\n"
            "No results found.\n\n"
            "🔔 <b>Want this daily?</b>\n"
            "Tap <b>Subscribe</b> below."
        )
    else:
        msg = header + "\n\n" + format_jobs(results)

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=start_keyboard(),
    )

# ----------------- DAILY PUSH -----------------

async def push_daily_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application

    for user in all_users():
        prefs = user.get("prefs", {})
        if not any(prefs.values()):
            continue

        parts = []
        if prefs.get("jobs_au"):
            parts.append("🔥 <b>AU Jobs</b>\n\n" + format_jobs(get_jobs("software engineer", "AU")))
        if prefs.get("jobs_in"):
            parts.append("🔥 <b>India Jobs</b>\n\n" + format_jobs(get_jobs("software engineer", "IN")))
        if prefs.get("ai_tools"):
            parts.append("🤖 <b>AI Tools</b>\n\n" + format_tools(get_ai_tools()))

        if parts:
            await app.bot.send_message(
                chat_id=user["user_id"],
                text="\n\n—\n\n".join(parts),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

# ----------------- STARTUP -----------------

async def on_startup(app):
    tz = ZoneInfo(DEFAULT_TZ)
    app.job_queue.run_daily(
        push_daily_job,
        time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE, tzinfo=tz),
        name="daily_push",
    )

def run():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CallbackQueryHandler(sub_callback, pattern=r"^(ui:open_subscribe|sub:.*)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))

    app.post_init = on_startup
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run()
