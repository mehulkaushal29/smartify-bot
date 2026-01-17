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

# ----------------- Country detection -----------------
COUNTRY_MAP = {
    "australia": "AU",
    "au": "AU",
    "india": "IN",
    "in": "IN",
    "china": "CN",
    "cn": "CN",
    "singapore": "SG",
    "sg": "SG",
    "uae": "AE",
    "ae": "AE",
    "new zealand": "NZ",
    "nz": "NZ",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "england": "GB",
    "canada": "CA",
    "ca": "CA",
    "germany": "DE",
    "de": "DE",
    "france": "FR",
    "fr": "FR",
}

# ----------------- Helpers -----------------

def parse_jobs_args(args):
    """
    /jobs <keyword> [country_code] [loc=City]
    """
    country = "AU"
    location = None
    tokens = []

    for a in args:
        al = a.lower().strip()

        # 2-letter country code
        if re.fullmatch(r"[a-z]{2}", al):
            country = al.upper()
        elif al.startswith("loc="):
            location = a.split("=", 1)[1]
        else:
            tokens.append(a)

    keyword = " ".join(tokens).strip() or "software engineer"
    return keyword, country, location


def parse_free_text_to_query(text: str):
    """
    Free text examples:
      - "python au"
      - "nurse india"
      - "hotel management china"
    """
    t = (text or "").lower().strip()
    t = re.sub(r"[,\.;:]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    location = None

    # location: loc=Melbourne
    m = re.search(r"loc=([a-z\s]+)", t, flags=re.I)
    if m:
        location = m.group(1).strip()
        t = re.sub(r"loc=([a-z\s]+)", "", t, flags=re.I).strip()

    # detect country by name or code
    country = None

    # Try multi-word names first (e.g. "new zealand", "united states")
    for name, code in sorted(COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(name)}\b", t):
            country = code
            t = re.sub(rf"\b{re.escape(name)}\b", "", t).strip()
            break

    if not country:
        country = "AU"  # fallback default

    keyword = t.strip() or "software engineer"
    return keyword, country, location


def _get_user_prefs(user_id: int) -> dict:
    user = get_user(user_id)
    prefs = user.get("prefs", {}) if user else {}
    prefs.setdefault("jobs_daily", False)
    prefs.setdefault("ai_tools", False)
    prefs.setdefault("country", "AU")
    prefs.setdefault("keyword", "software engineer")
    prefs.setdefault("location", None)
    return prefs


def build_subscribe_keyboard(prefs: dict, daily_time: str) -> InlineKeyboardMarkup:
    def label(on: bool, text: str) -> str:
        return f"{'✅' if on else '⭕️'} {text}"

    kb = [
        [InlineKeyboardButton(label(prefs.get("jobs_daily", False), "Daily Job Alerts"),
                              callback_data="sub:toggle:jobs_daily")],
        [InlineKeyboardButton(label(prefs.get("ai_tools", False), "AI Tools"),
                              callback_data="sub:toggle:ai_tools")],
        [
            InlineKeyboardButton("✅ Done (save)", callback_data="sub:done"),
            InlineKeyboardButton("🛑 Unsubscribe all", callback_data="sub:clear"),
        ],
        [InlineKeyboardButton(f"⏰ Daily at {daily_time}", callback_data="sub:nop")],
    ]
    return InlineKeyboardMarkup(kb)


def start_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton("✅ Subscribe", callback_data="ui:open_subscribe")]]
    if CHANNEL_ID:
        buttons.append([InlineKeyboardButton("📢 Open Channel", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")])
    return InlineKeyboardMarkup(buttons)


# ----------------- Channel posting -----------------

async def post_channel_summary(app):
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID not set — skipping channel post.")
        return

    parts = []

    au = format_jobs(get_jobs("software engineer", "AU"))
    if au.strip():
        parts.append("🔥 <b>AU Jobs</b>:\n\n" + au)

    in_ = format_jobs(get_jobs("software engineer", "IN"))
    if in_.strip():
        parts.append("🔥 <b>India Jobs</b>:\n\n" + in_)

    tools = format_tools(get_ai_tools())
    if tools.strip():
        parts.append("🤖 <b>AI Tools</b>:\n\n" + tools)

    if not parts:
        logger.info("Nothing to post to channel today.")
        return

    text = "\n\n—\n\n".join(parts)

    buttons = [
        [InlineKeyboardButton("🤖 Open Bot / Subscribe", url="https://t.me/smartify_jobs_bot")],
        [InlineKeyboardButton("📢 Join Smartify Jobs", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
    ]
    markup = InlineKeyboardMarkup(buttons)

    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=markup,
        )
        logger.info(f"Posted daily summary to channel {CHANNEL_ID}")
    except Exception as e:
        logger.warning(f"Failed to post to channel {CHANNEL_ID}: {e}")


# ----------------- Command Handlers -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id)

    prefs = _get_user_prefs(user_id)
    upsert_user(user_id, prefs=prefs)

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

    if not results:
        return await update.message.reply_text(
            header + "\n\nNo results found.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    await update.message.reply_text(
        header + "\n\n" + format_jobs(results),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id)

    prefs = _get_user_prefs(user_id)
    daily_time = f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"

    await update.message.reply_text(
        "Choose what you want daily:",
        reply_markup=build_subscribe_keyboard(prefs, daily_time),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    prefs = _get_user_prefs(user_id)
    daily_time = f"{DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"

    data = query.data

    if data == "ui:open_subscribe":
        return await query.edit_message_text(
            "Choose what you want daily:",
            reply_markup=build_subscribe_keyboard(prefs, daily_time),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    if data == "sub:nop":
        return

    if data == "sub:clear":
        prefs["jobs_daily"] = False
        prefs["ai_tools"] = False
        upsert_user(user_id, prefs=prefs)
        return await query.edit_message_text(
            "✅ Unsubscribed from all daily messages.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    if data == "sub:done":
        upsert_user(user_id, prefs=prefs)
        return await query.edit_message_text(
            "✅ Saved!",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    if data.startswith("sub:toggle:"):
        key = data.split(":")[-1]
        prefs[key] = not prefs.get(key, False)
        upsert_user(user_id, prefs=prefs)
        return await query.edit_message_reply_markup(
            reply_markup=build_subscribe_keyboard(prefs, daily_time)
        )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefs = _get_user_prefs(user_id)
    prefs["jobs_daily"] = False
    prefs["ai_tools"] = False
    upsert_user(user_id, prefs=prefs)
    await update.message.reply_text("✅ Unsubscribed from all daily pushes.")


async def prefs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prefs = _get_user_prefs(update.effective_user.id)
    msg = (
        "<b>Your preferences</b>\n"
        f"• Daily jobs: {prefs.get('jobs_daily')}\n"
        f"• Country: {prefs.get('country')}\n"
        f"• Role: {prefs.get('keyword')}\n"
        f"• Location: {prefs.get('location') or '(none)'}\n"
        f"• AI tools: {prefs.get('ai_tools')}\n"
        f"\nDaily: {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def settz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Send a valid timezone, e.g. /settz Asia/Kolkata")

    tz_str = context.args[0]
    try:
        ZoneInfo(tz_str)
    except Exception:
        return await update.message.reply_text("Invalid timezone. Try Asia/Kolkata or Australia/Melbourne.")

    upsert_user(update.effective_user.id, tz=tz_str)
    await update.message.reply_text(f"Timezone set to {tz_str}.")


# ----------------- Text Search -----------------

async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    kw, cc, loc = parse_free_text_to_query(text)
    results = get_jobs(kw, cc, location=loc)

    header = f"🔎 <b>Jobs for “{kw}” — {cc}</b>" + (f" — {loc}" if loc else "")

    if not results:
        msg = header + "\n\nNo results found.\n\nTip: try adding a country (e.g. “hotel management china”) or use /subscribe for daily alerts."
    else:
        msg = header + "\n\n" + format_jobs(results)

    # show a subscribe CTA under results
    await update.message.reply_text(
        msg + "\n\n🔔 <b>Want this daily?</b>\nTap <b>Subscribe</b> below.",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=start_keyboard(),
    )


# ----------------- Daily Push -----------------

async def push_daily_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    logger.info("Running daily push job…")

    for row in all_users():
        uid = row["user_id"]
        p = row.get("prefs", {}) or {}

        jobs_daily = p.get("jobs_daily", False)
        ai_tools = p.get("ai_tools", False)

        if not jobs_daily and not ai_tools:
            continue

        parts = []

        if jobs_daily:
            country = p.get("country", "AU")
            keyword = p.get("keyword", "software engineer")
            location = p.get("location", None)

            header = f"🔥 <b>Daily Jobs — {country}</b>\nRole: <b>{keyword}</b>"
            results = get_jobs(keyword, country, location=location)
            parts.append(header + "\n\n" + (format_jobs(results) if results else "No jobs found today."))

        if ai_tools:
            parts.append("🤖 <b>AI Tools</b>:\n\n" + format_tools(get_ai_tools()))

        try:
            await app.bot.send_message(
                chat_id=uid,
                text="\n\n—\n\n".join(parts),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.warning(f"Failed to push to {uid}: {e}")

    await post_channel_summary(app)


async def on_startup(application):
    tz = ZoneInfo(DEFAULT_TZ)
    application.job_queue.run_daily(
        push_daily_job,
        time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE, tzinfo=tz),
        name="daily_push"
    )
    logger.info(f"Daily job scheduled for {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} {DEFAULT_TZ}")


def run():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing. Check Railway variables")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("prefs", prefs_cmd))
    app.add_handler(CommandHandler("settz", settz))

    app.add_handler(CallbackQueryHandler(sub_callback, pattern=r"^(ui:open_subscribe|sub:.*)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))

    app.post_init = on_startup

    # Railway-friendly polling
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    run()
