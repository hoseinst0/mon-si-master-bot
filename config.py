"""
config.py
تنظیمات اصلی ربات مارکت اکانت CoD Mobile
"""
import os

# ---------- تنظیمات ربات ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "cod_market")

# آیدی عددی ادمین‌ها (برای دسترسی به پنل مدیریت و حل اختلاف)
ADMIN_IDS = [
    123456789,  # <-- آیدی عددی خودتو اینجا بذار
]

# آیدی چنل عمومی برای نمایش شمارش معکوس معاملات escrow (شفافیت عمومی)
PUBLIC_ESCROW_CHANNEL_ID = None  # مثلا: -1001234567890

# ---------- تنظیمات اقتصادی ----------
CURRENCY_NAME = "Zen"                 # واحد پول داخلی ربات
PLATFORM_FEE_PERCENT = 5              # کارمزد پلتفرم از هر معامله موفق
VIP_FEE_PERCENT = 2                   # کارمزد کاهش‌یافته برای کاربران VIP
INSURANCE_FEE_PERCENT = 3             # هزینه بیمه اختیاری معامله
INSURANCE_WINDOW_HOURS = 24           # بازه زمانی پوشش بیمه بعد از تحویل
REFERRAL_COMMISSION_PERCENT = 1       # کمیسیون رفرال از کارمزد پلتفرم

# ---------- تنظیمات Escrow ----------
ESCROW_DEFAULT_MINUTES = 45           # مدت پیش‌فرض قفل بودن پول در وست/امانی
ESCROW_MIN_MINUTES = 30
ESCROW_MAX_MINUTES = 60

# ---------- تنظیمات Trust Score ----------
TRUST_SCORE_START = 50
TRUST_SCORE_SUCCESS_DELTA = 5
TRUST_SCORE_COMPLAINT_DELTA = -15
TRUST_SCORE_SCAM_CONFIRMED_DELTA = -50
TRUST_SCORE_MIN_TO_SELL = 0            # زیر این عدد، فروشنده نمی‌تونه لیست جدید بسازه

# ---------- تنظیمات مزایده (Auction) ----------
AUCTION_MIN_DURATION_MINUTES = 10
AUCTION_MAX_DURATION_MINUTES = 180
AUCTION_MIN_BID_INCREMENT_PERCENT = 5   # حداقل افزایش نسبت به پیشنهاد قبلی

# ---------- رنک‌های اکانت (برای Account Health Check) ----------
ACCOUNT_RANKS = [
    "Rookie", "Veteran", "Elite", "Pro",
    "Master", "Grandmaster", "Legendary", "Mythic"
]

# ---------- پنل وب (Web Dashboard) ----------
WEB_PANEL_ENABLED = os.getenv("WEB_PANEL_ENABLED", "true").lower() == "true"
WEB_PANEL_PORT = int(os.getenv("PORT", os.getenv("WEB_PANEL_PORT", "8080")))
WEB_PANEL_USERNAME = os.getenv("WEB_PANEL_USERNAME", "admin")
WEB_PANEL_PASSWORD = os.getenv("WEB_PANEL_PASSWORD", "change-me-please")
WEB_PANEL_SECRET_KEY = os.getenv("WEB_PANEL_SECRET_KEY", "please-change-this-secret-key")

# ---------- پنل ادمین داخل ربات ----------
BROADCAST_DELAY_SECONDS = 0.05
RECENT_ITEMS_LIMIT = 15
