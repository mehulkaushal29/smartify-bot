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
from ai_tools import get_ai_tools
from database import get_user, upsert_user, all_users
from utils import WELCOME, format_jobs, format_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartify")


# ----------------- PARSING (KEY FIX) -----------------

def parse_free_text(text: str):
    """
    Extract keyword + location from free text.
    Examples:
    - admin jobs in scotland
    - nurse california
    - hotel jobs china
    """
    text = text.lower().strip()

    # remove filler words
    text = re.sub(r"\b(jobs?|roles?|vacancies?|openings?)\b", "", text)
    text = re.sub(r"\bin\b", "", text)

    tokens = text.split()

    if len(tokens) >= 2:
        keyword = " ".join(tokens[:-1])
        location = tokens[-1]
    else:
        keyword = text
        location = None

    return keyword.strip(), location


# ----------------- KEYBOARD -----------------

def subscribe_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔔 Subscribe for daily updates", callback_data="subscribe")]]
    )


# ----------------- COMMANDS -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user.id)
    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.HTML,
        reply_markup=subscribe_keyboard(),
    )


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    keyword, location = parse_free_text(text)

    results = get_jobs(keyword=keyword, location=location)

    header = f"🔎 <b>Jobs for “{keyword}”</b>"
    if location:
        header += f" — <b>{location.title()}</b>"

    if not results:
        return await update.message.reply_text(
            header + "\n\nNo results found.",
            parse_mode=ParseMode.HTML,
            reply_markup=subscribe_keyboard(),
        )

    await update.message.reply_text(
        header + "\n\n" + format_jobs(results),
        parse_mode=ParseMode.HTML,
        reply_markup=subscribe_keyboard(),
        disable_web_page_preview=True,
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id, subscribed=True)
    await update.message.reply_text("✅ You’re subscribed for daily updates!")


# ----------------- DAILY PUSH -----------------

async def push_daily_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application

    for user in all_users():
        if not user.get("subscribed"):
            continue

        keyword = user.get("last_keyword", "jobs")
        location = user.get("last_location")

        results = get_jobs(keyword=keyword, location=location)
        if not results:
            continue

        header = f"🔥 <b>Daily Jobs for {keyword}</b>"
        if location:
            header += f" — {location.title()}"

        await app.bot.send_message(
            chat_id=user["user_id"],
            text=header + "\n\n" + format_jobs(results),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )


async def on_startup(app):
    tz = ZoneInfo(DEFAULT_TZ)
    app.job_queue.run_daily(
        push_daily_job,
        time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE, tzinfo=tz),
    )


# ----------------- APP -----------------

def run():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(subscribe, pattern="subscribe"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))

    app.post_init = on_startup
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run()
