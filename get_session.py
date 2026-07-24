"""
این اسکریپت رو روی کامپیوتر یا گوشیت (با Termux/Pydroid) اجرا کن.
یه بار اجرا می‌شه، کد پیامکی رو ازت می‌پرسه، و در آخر یه SESSION STRING بهت می‌ده.
اون رشته رو کپی کن و بفرست - دیگه لازم نیست دوباره این اسکریپت رو اجرا کنی.

نصب پیش‌نیاز (یه بار):
    pip install telethon --break-system-packages
اجرا:
    python get_session.py
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# اینا رو با مقادیر خودت پر کن:
API_ID = 32347586
API_HASH = "1e9474b9514abab171052dabce77ef17"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    session_string = client.session.save()
    print("\n\n=== SESSION STRING (این رو کپی کن و برام بفرست) ===\n")
    print(session_string)
    print("\n====================================================\n")
    print("⚠️ این رشته معادل رمز اکانتته - جایی آپلودش نکن، فقط تو کانفیگ ربات بذارش.")
