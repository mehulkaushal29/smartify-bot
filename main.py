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

from config import TELEGRAM_BOT_TOKEN, DEFAULT_TZ, DAILY_HOUR, DAILY_MINUTE
from jobs_api import get_jobs
from database import upsert_user, all_users
from utils import WELCOME, format_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartify")


# ----------------- PARSING -----------------

def parse_free_text(text: str):
    """
    Extract keyword + location from free text.
    Examples:
    - admin jobs in scotland
    - nurse california
    - hotel jobs china
    """
    text = (text or "").lower().strip()

    # remove filler words
    text = re.sub(r"\b(jobs?|roles?|vacancies?|openings?)\b", "", text)
    text = re.sub(r"\bin\b", "", text)

    # clean spaces
    text = re.sub(r"\s+", " ", text).strip()

    tokens = text.split()

    if len(tokens) >= 2:
        keyword = " ".join(tokens[:-1]).strip()
        location = tokens[-1].strip()
    else:
        keyword = text.strip()
        location = None

    # fallback
    if not keyword:
        keyword = "jobs"

    return keyword, location


# ----------------- KEYBOARD -----------------

def subscribe_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔔 Subscribe for daily updates", callback_data="subscribe")]]
    )


# ----------------- ERROR HANDLER -----------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception while processing update", exc_info=context.error)


# ----------------- COMMANDS -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id)
    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=subscribe_keyboard(),
    )


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Guard: only proceed if we truly have a message text
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text

    keyword, location = parse_free_text(text)

    # ✅ Save last search for daily push
    upsert_user(user_id, last_keyword=keyword, last_location=location)

    # ✅ Jooble/Jobs API call
    results = get_jobs(keyword=keyword, location=location)

    header = f"🔎 <b>Jobs for “{keyword}”</b>"
    if location:
        header += f" — <b>{location.title()}</b>"

    if not results:
        return await update.message.reply_text(
            header + "\n\nNo results found.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=subscribe_keyboard(),
        )

    await update.message.reply_text(
        header + "\n\n" + format_jobs(results),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=subscribe_keyboard(),
    )


async def subscribe_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ✅ Button-click subscribe (CallbackQuery)
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    upsert_user(user_id, subscribed=True)

    # Edit the original bot message (best UX)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("✅ You’re subscribed for daily updates!")


async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Optional: /subscribe command
    """
    user_id = update.effective_user.id
    upsert_user(user_id, subscribed=True)
    await update.message.reply_text("✅ You’re subscribed for daily updates!")


# ----------------- DAILY PUSH -----------------

async def push_daily_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application

    for user in all_users():
        if not user.get("subscribed"):
            continue

        uid = user["user_id"]
        keyword = user.get("last_keyword") or "jobs"
        location = user.get("last_location")

        results = get_jobs(keyword=keyword, location=location)
        if not results:
            continue

        header = f"🔥 <b>Daily Jobs for “{keyword}”</b>"
        if location:
            header += f" — <b>{location.title()}</b>"

        try:
            await app.bot.send_message(
                chat_id=uid,
                text=header + "\n\n" + format_jobs(results),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning(f"Failed to push to {uid}: {e}")


async def on_startup(app):
    tz = ZoneInfo(DEFAULT_TZ)
    app.job_queue.run_daily(
        push_daily_job,
        time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE, tzinfo=tz),
        name="daily_push",
    )
    logger.info(f"Daily push scheduled at {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}")


# ----------------- APP -----------------

def run():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Error handler (so Railway shows real exceptions)
    app.add_error_handler(error_handler)

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))

    # Button click subscribe
    app.add_handler(CallbackQueryHandler(subscribe_cb, pattern=r"^subscribe$"))

    # ✅ Only private chat free-text searches
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, text_search)
    )

    app.post_init = on_startup

    # ✅ Only accept what you handle
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    run()
