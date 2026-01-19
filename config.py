import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ❌ OLD (Adzuna – can stay or be removed)
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

# ✅ NEW (Jooble – REQUIRED)
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")

DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Australia/Melbourne")
DAILY_HOUR = int(os.getenv("DAILY_HOUR", 9))
DAILY_MINUTE = int(os.getenv("DAILY_MINUTE", 0))

RESULTS_PER_PAGE = 5

CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
