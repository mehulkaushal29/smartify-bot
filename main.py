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


# ----------------- Helpers -----------------

COUNTRY_MAP = {
    "australia": "AU",
    "au": "AU",
    "india": "IN",
    "in": "IN",
    "usa": "US",
    "us": "US",
    "united states": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "canada": "CA",
    "new zealand": "NZ",
    "nz": "NZ",
    "singapore": "SG",
    "uae": "AE",
    "germany": "DE",
    "france": "FR",
}


def parse_jobs_args(args):
    country = "AU"
    location = None
    tokens = []

    for a in args:
        al = a.lower().strip()
        if al in COUNTRY_MAP:
            country = COUNTRY_MAP[al]
        elif al.startswith("loc="):
            location = a.split("=", 1)[1]
        else:
            tokens.append(a)

    keyword = " ".join(tokens).strip() or "software engineer"
    return keyword, country, location


def parse_free_text_to_query(text: str):
    t = (text or "").strip()
    t = re.sub(r"[,\.;:]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    country = "AU"
    location = None

    lower = t.lower()
    for name, code in COUNTRY_MAP.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            country = code
            t = re.sub(rf"\b{re.escape(name)}\b", "", t, flags=re.I).strip()
            break

    m = re.search(r"loc=([A-Za-z\s]+)", t, flags=re.I)
    if m:
        location = m.group(1).strip()
        t = re.sub(r"loc=[A-Za-z\s]+", "", t, flags=re.I).strip()

    keyword = t.strip() or "software engineer"
    return keyword, country, location


def get_prefs(user_id: int) -> dict:
    user = get_user(user_id)
    prefs = user.get("prefs", {}) if user else {}
    prefs.setdefault("jobs_daily", False)
    prefs.setdefault("ai_tools", False)
    prefs.setdefault("country", "AU")
    prefs.setdefault("keyword", "software engineer")
    prefs.setdefault("location", None)
    return prefs


# ----------------- Keyboards -----------------

def start_keyboard():
    buttons = [[InlineKeyboardButton("🔔 Subscribe", callback_data="ui:open_subscribe")]]
    if CHANNEL_ID:
        buttons.append([InlineKeyboardButton("📢 Open Channel", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")])
    return InlineKeyboardMarkup(buttons)


def quick_sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Get daily alerts for this", callback_data="quick:daily_on")],
        [InlineKeyboardButton("⚙️ Manage subscription", callback_data="ui:open_subscribe")],
    ])


def build_subscribe_keyboard(prefs: dict):
    def label(on, text): return f"{'✅' if on else '⭕️'} {text}"

    daily_time = f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label(prefs["jobs_daily"], "Daily Job Alerts"), callback_data="sub:toggle:jobs_daily")],
        [InlineKeyboardButton(label(prefs["ai_tools"], "AI Tools"), callback_data="sub:toggle:ai_tools")],
        [
            InlineKeyboardButton("✅ Done", callback_data="sub:done"),
            InlineKeyboardButton("🛑 Unsubscribe", callback_data="sub:clear"),
        ],
        [InlineKeyboardButton(f"⏰ Daily at {daily_time}", callback_data="sub:nop")],
    ])


# ----------------- Commands -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user.id)
    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=start_keyboard(),
    )


async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kw, cc, loc = parse_jobs_args(context.args)
    results = get_jobs(kw, cc, location=loc)
    header = f"🔎 <b>Jobs for “{kw}” — {cc}</b>" + (f" — {loc}" if loc else "")
    await update.message.reply_text(
        header + "\n\n" + (format_jobs(results) if results else "No results found."),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def aitools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prefs = get_prefs(update.effective_user.id)
    prefs["ai_tools"] = True
    upsert_user(update.effective_user.id, prefs=prefs)

    await update.message.reply_text(
        "🤖 <b>Trending AI tools</b>\n\n" + format_tools(get_ai_tools()),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ----------------- Text Search (KEY FIX) -----------------

async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kw, cc, loc = parse_free_text_to_query(update.message.text)

    prefs = get_prefs(user_id)
    prefs["keyword"] = kw
    prefs["country"] = cc
    prefs["location"] = loc
    upsert_user(user_id, prefs=prefs)

    results = get_jobs(kw, cc, location=loc)
    header = f"🔎 <b>Jobs for “{kw}” — {cc}</b>" + (f" — {loc}" if loc else "")
    msg = header + "\n\n" + (format_jobs(results) if results else "No results found.")

    await update.message.reply_text(
        msg + "\n\n<b>Want this daily?</b>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=quick_sub_keyboard(),
    )


# ----------------- Callbacks -----------------

async def sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    prefs = get_prefs(user_id)

    if q.data == "quick:daily_on":
        prefs["jobs_daily"] = True
        upsert_user(user_id, prefs=prefs)
        return await q.edit_message_text(
            "✅ You’ll now receive <b>daily job alerts</b> at 9 AM.",
            parse_mode=ParseMode.HTML,
        )

    if q.data == "ui:open_subscribe":
        return await q.edit_message_text(
            "Choose what you want daily:",
            reply_markup=build_subscribe_keyboard(prefs),
            parse_mode=ParseMode.HTML,
        )

    if q.data.startswith("sub:toggle:"):
        key = q.data.split(":")[-1]
        prefs[key] = not prefs.get(key, False)
        upsert_user(user_id, prefs=prefs)
        return await q.edit_message_reply_markup(build_subscribe_keyboard(prefs))

    if q.data == "sub:clear":
        prefs["jobs_daily"] = False
        prefs["ai_tools"] = False
        upsert_user(user_id, prefs=prefs)
        return await q.edit_message_text("❌ Unsubscribed from all.")

    if q.data == "sub:done":
        upsert_user(user_id, prefs=prefs)
        return await q.edit_message_text("✅ Preferences saved.")


# ----------------- Daily Push -----------------

async def push_daily_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    for row in all_users():
        uid = row["user_id"]
        p = row.get("prefs", {})
        if not p.get("jobs_daily") and not p.get("ai_tools"):
            continue

        parts = []
        if p.get("jobs_daily"):
            parts.append(
                f"🔥 <b>Daily Jobs — {p['country']}</b>\n\n" +
                format_jobs(get_jobs(p["keyword"], p["country"], p.get("location")))
            )
        if p.get("ai_tools"):
            parts.append("🤖 <b>AI Tools</b>\n\n" + format_tools(get_ai_tools()))

        try:
            await app.bot.send_message(
                chat_id=uid,
                text="\n\n—\n\n".join(parts),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning(f"Push failed for {uid}: {e}")


async def on_startup(app):
    tz = ZoneInfo(DEFAULT_TZ)
    app.job_queue.run_daily(
        push_daily_job,
        time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE, tzinfo=tz),
        name="daily_push",
    )


# ----------------- Run -----------------

def run():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CommandHandler("aitools", aitools))

    app.add_handler(CallbackQueryHandler(sub_callback, pattern=r"^(ui:|sub:|quick:)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))

    app.post_init = on_startup
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run()