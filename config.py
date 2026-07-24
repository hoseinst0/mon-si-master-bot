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
    7508182482,
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

# ---------- جدول نرخ حق واسط (بر اساس ارزش معامله) ----------
# هر ردیف یه بازه از ارزش معامله رو پوشش می‌ده. "max": None یعنی بدون سقف (آخرین ردیف).
# ردیف‌های اول/وسط با مبلغ ثابت (fee) و ردیف آخر (بدون سقف) با درصد (fee_percent) محاسبه می‌شن.
# vip_fee / vip_fee_percent نرخ کاهش‌یافته برای مشترکین VIP (Prime) هست.
MIDDLEMAN_FEE_TIERS = [
    {"min": 0,          "max": 1_000_000,   "fee": 50_000,    "vip_fee": 30_000},
    {"min": 1_000_000,  "max": 5_000_000,   "fee": 250_000,   "vip_fee": 150_000},
    {"min": 5_000_000,  "max": 10_000_000,  "fee": 550_000,   "vip_fee": 350_000},
    {"min": 10_000_000, "max": 14_900_000,  "fee": 990_000,   "vip_fee": 650_000},
    {"min": 14_900_000, "max": 25_000_000,  "fee": 1_650_000, "vip_fee": 1_100_000},
    {"min": 25_000_000, "max": None,        "fee_percent": 6, "vip_fee_percent": 4},
]

# ---------- تنظیمات احراز هویت (KYC) ----------
# معاملاتی که قیمتشون بالاتر از این سقفه، تا وقتی کاربر احراز هویت نشده باشه ادامه پیدا نمی‌کنن.
KYC_REQUIRED_ABOVE = 15_000_000

# ---------- تشخیص خودکار مبلغ از عکس رسید (OCR) ----------
# نیازمند نصب کتابخونه‌های pytesseract + Pillow *و* باینری سیستمی tesseract-ocr
# (روی Railway باید با nixpacks.toml یا Dockerfile نصب بشه، صرفاً pip کافی نیست).
# اگه False باشه یا نصب نباشه، ربات به‌جای تشخیص خودکار، مبلغ رو دستی از ادمین می‌پرسه (بدون کرش).
RECEIPT_OCR_ENABLED = os.getenv("RECEIPT_OCR_ENABLED", "true").lower() == "true"

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

# ---------- یوزربات (ساخت خودکار گروه معامله - Telethon) ----------
# از my.telegram.org گرفتی: api_id و api_hash
USERBOT_API_ID = int(os.getenv("USERBOT_API_ID", "32347586"))
USERBOT_API_HASH = os.getenv("USERBOT_API_HASH", "PUT_YOUR_API_HASH_HERE")
# session string که با get_session.py گرفتی
USERBOT_SESSION = os.getenv("USERBOT_SESSION", "PUT_YOUR_SESSION_STRING_HERE")

# یوزرنیم ادمین‌هایی که یوزربات باید خودکار به هر گروه معامله اضافه کنه (بدون @)
ADMIN_USERNAMES = [
    "PV_MASTERCODM",
]

# محدودیت استفاده از هر لینک دعوت گروه معامله (چند نفر بتونن با این لینک عضو بشن)
DEAL_GROUP_INVITE_USAGE_LIMIT = 4
