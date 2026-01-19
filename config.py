import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")   # ✅ ADD THIS

DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Australia/Melbourne")
DAILY_HOUR = int(os.getenv("DAILY_HOUR", 9))
DAILY_MINUTE = int(os.getenv("DAILY_MINUTE", 0))

RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", 5))
