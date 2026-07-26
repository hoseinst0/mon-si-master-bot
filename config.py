# ============================================================
#  RAVENMORE ACADEMY RPG BOT — Config
# ============================================================
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGODB_URL = os.getenv("MONGODB_URL", "")

# مالک اصلی ربات (همیشه ادمین است، حتی اگر توی دیتابیس نباشد)
OWNER_ID = int(os.getenv("OWNER_ID", "8301907301"))

# هر چند ساعت واقعی = ۱ روز آکادمی (طبق سند: هر ۲ روز واقعی = ۱ روز آکادمی)
HOURS_PER_ACADEMY_DAY = int(os.getenv("HOURS_PER_ACADEMY_DAY", str(48)))

# هر چند روز آکادمی یک نامه جدید ارسال شود
LETTER_INTERVAL_DAYS = 2

MAX_MOOD = 10
START_MOOD = 10
