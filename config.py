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

# ------------------------------------------------------------
#  ایونت‌های تاریک — زمان‌بندی خودکار
# ------------------------------------------------------------
DARK_EVENT_CHECK_INTERVAL_SECONDS = int(os.getenv("DARK_EVENT_CHECK_INTERVAL_SECONDS", str(20 * 60)))
DARK_EVENT_TRIGGER_CHANCE = float(os.getenv("DARK_EVENT_TRIGGER_CHANCE", "0.12"))  # هر بار چک، به‌ازای هر بازیکن واجد شرایط
DARK_EVENT_MIN_COOLDOWN_HOURS = float(os.getenv("DARK_EVENT_MIN_COOLDOWN_HOURS", "18"))

# ------------------------------------------------------------
#  نامه‌ها/کوئست‌ها در زمان کاملاً ثابت نروند؛ کمی رندوم (روز آکادمی ± این مقدار)
# ------------------------------------------------------------
LETTER_INTERVAL_JITTER_DAYS = 1
